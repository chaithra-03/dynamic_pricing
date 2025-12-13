from time import perf_counter
from threading import Lock
import uuid
from datetime import datetime
from typing import List, Tuple, Optional,Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_,select, update
from app.models.product import Product
from app.models.flash_sale import FlashSale, FlashSaleProduct, FlashSaleOrder
from app.models.product import Product
from app.schemas.flash_sale import (
    FlashSaleCreate,
    FlashSaleResponse,
    FlashSalePurchaseRequest,
    PurchaseTrackingResponse,
    PurchaseEntry,
    RemainingLimitResponse,
    ValidatePurchaseRequest,
    ValidatePurchaseResponse,
)
from fastapi import HTTPException, BackgroundTasks
import uuid

_USER_PURCHASES: Dict[tuple, int] = {}
_USER_PURCHASES_LOCK = Lock()

def generate_order_id():
    return "ORD_" + uuid.uuid4().hex[:10].upper()

COOLING_PERIOD_SECONDS = 60

def _generate_flash_sale_id() -> str:
    return f"FLASH_{uuid.uuid4().hex[:8].upper()}"


def _generate_order_id() -> str:
    return f"ORD_{uuid.uuid4().hex[:8].upper()}"

def _inc_user_purchase_local(user_id: str, flash_sale_id: str, product_id: str, qty: int):
    key = (user_id, flash_sale_id, product_id)
    with _USER_PURCHASES_LOCK:
        _USER_PURCHASES[key] = _USER_PURCHASES.get(key, 0) + qty
        return _USER_PURCHASES[key]
    
def _get_user_purchase_local(user_id: str, flash_sale_id: str, product_id: str) -> int:
    return _USER_PURCHASES.get((user_id, flash_sale_id, product_id), 0)

def _bg_log_order(order_id: str):
    print(f"[BG] log order {order_id}")


def _bg_notify_user(order_id: str, user_id: str):
    print(f"[BG] notify user {user_id} for order {order_id}")



# ---------- CREATE FLASH SALE ----------

def create_flash_sale(db: Session, data: FlashSaleCreate) -> FlashSale:
    flash_sale_id = data.flash_sale_id

    flash_sale = FlashSale(
        flash_sale_id=flash_sale_id,
        name=data.name,
        description=data.description,
        start_time=data.start_time,
        end_time=data.end_time,
        status=data.status or "scheduled",
        visibility=data.visibility,
    )
    db.add(flash_sale)
    db.flush() 

    for item in data.products:
        product = (
            db.query(Product)
            .filter(Product.product_id == item.product_id)
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item.product_id} not found",
            )

        original_price = (
            item.original_price
            if item.original_price is not None
            else product.current_price
        )

        if original_price <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid original price for product {item.product_id}",
            )

        discount_percentage = (
            item.discount_percentage
            if item.discount_percentage is not None
            else (1 - (item.flash_sale_price / original_price)) * 100
        )

        fs_product = FlashSaleProduct(
            flash_sale_id=flash_sale.flash_sale_id,
            product_id=item.product_id,
            flash_sale_price=item.flash_sale_price,
            original_price=original_price,
            discount_percentage=discount_percentage,
            stock_allocated=item.stock_allocated,
            stock_remaining=item.stock_allocated,
            max_per_user=item.max_per_user,
            version=1,
        )
        db.add(fs_product)

    db.commit()
    db.refresh(flash_sale)
    return flash_sale


# ---------- GET / LIST FLASH SALES ----------

def get_flash_sale(db: Session, flash_sale_id: str) -> Optional[FlashSale]:
    sale = (
        db.query(FlashSale)
        .filter(FlashSale.flash_sale_id == flash_sale_id)
        .first()
    )

    if not sale:
        return None

    current = sale.visitors or 0
    sale.visitors = current + 1

    db.add(sale)
    db.commit()
    db.refresh(sale)

    return sale


def list_flash_sales(
    db: Session, status: Optional[str] = None
) -> List[FlashSale]:
    query = db.query(FlashSale)
    if status:
        query = query.filter(FlashSale.status == status)
    return query.order_by(FlashSale.start_time.desc()).all()


# ---------- STATE TRANSITIONS ----------

def activate_flash_sale(db: Session, flash_sale_id: str) -> Optional[FlashSale]:
    flash_sale = get_flash_sale(db, flash_sale_id)
    if not flash_sale:
        return None

    now = datetime.utcnow()
    if flash_sale.start_time > now:
        raise HTTPException(
            status_code=400,
            detail="Flash sale start_time is in the future; cannot activate yet.",
        )

    if flash_sale.end_time < now:
        raise HTTPException(
            status_code=400,
            detail="Flash sale already ended; cannot activate.",
        )

    flash_sale.status = "active"
    db.commit()
    db.refresh(flash_sale)
    return flash_sale


def end_flash_sale(db: Session, flash_sale_id: str) -> Optional[FlashSale]:
    flash_sale = get_flash_sale(db, flash_sale_id)
    if not flash_sale:
        return None
    flash_sale.status = "ended"
    db.commit()
    db.refresh(flash_sale)
    return flash_sale


def cancel_flash_sale(db: Session, flash_sale_id: str) -> Optional[FlashSale]:
    flash_sale = get_flash_sale(db, flash_sale_id)
    if not flash_sale:
        return None
    flash_sale.status = "cancelled"
    db.commit()
    db.refresh(flash_sale)
    return flash_sale


# ---------- PURCHASE DURING FLASH SALE ----------

def purchase_in_flash_sale(
    db: Session,
    flash_sale_id: str,
    request: FlashSalePurchaseRequest,
    client_ip: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    require_max_per_user_check: bool = True,
) -> FlashSaleOrder:
 
    validation: ValidatePurchaseResponse = validate_purchase_request(
        db=db,
        flash_sale_id=flash_sale_id,
        data=ValidatePurchaseRequest(
            user_id=request.user_id,
            product_id=request.product_id,
            quantity=request.quantity,
            device_fingerprint=request.device_fingerprint,
            captcha_token=request.captcha_token,
        ),
        client_ip=client_ip,
    )

    if not validation.allowed:
        raise HTTPException(
            status_code=400,
            detail={"message": "Purchase blocked", "reasons": validation.reasons},
        )

    qty = int(request.quantity)
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    row = (
        db.execute(
            select(
                FlashSaleProduct.id,
                FlashSaleProduct.stock_remaining,
                FlashSaleProduct.max_per_user,
                FlashSaleProduct.flash_sale_price,
                FlashSaleProduct.original_price,
                FlashSaleProduct.version,
            ).where(
                and_(
                    FlashSaleProduct.flash_sale_id == flash_sale_id,
                    FlashSaleProduct.product_id == request.product_id,
                )
            ).limit(1)
        )
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Product not part of flash sale")

    fs_id = row.id
    stock_remaining = int(row.stock_remaining or 0)
    max_per_user = row.max_per_user
    sale_price = float(row.flash_sale_price)
    original_price = float(row.original_price or sale_price)
    version = int(row.version or 0)

    if require_max_per_user_check and max_per_user is not None:
        local_prev = _get_user_purchase_local(request.user_id, flash_sale_id, request.product_id)
        if local_prev + qty > int(max_per_user):
            raise HTTPException(status_code=403, detail="Per-user limit exceeded (local guard)")

    upd = (
        update(FlashSaleProduct)
        .where(
            and_(
                FlashSaleProduct.id == fs_id,
                FlashSaleProduct.stock_remaining >= qty,
            )
        )
        .values(
            stock_remaining=(FlashSaleProduct.stock_remaining - qty),
            version=(FlashSaleProduct.version + 1),
        )
    )

    res = db.execute(upd)
    if res.rowcount != 1:
        fresh = db.execute(select(FlashSaleProduct.stock_remaining).where(FlashSaleProduct.id == fs_id)).scalar_one_or_none()
        fresh_stock = int(fresh or 0)
        raise HTTPException(status_code=409, detail=f"Insufficient stock (remaining={fresh_stock})")

    order_id = _generate_order_id()
    total_price = sale_price * qty
    savings = (original_price * qty) - total_price

    new_order = FlashSaleOrder(
        order_id=order_id,
        flash_sale_id=flash_sale_id,
        product_id=request.product_id,
        user_id=request.user_id,
        quantity=qty,
        flash_sale_price=sale_price,
        total_price=total_price,
        savings=savings,
        status="confirmed",
        payment_method=request.payment_method,
        client_ip=client_ip,
        device_fingerprint=request.device_fingerprint,
        purchase_timestamp=datetime.utcnow(),
    )
    db.add(new_order)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to complete purchase; please try again") from e

    db.refresh(new_order)

    _inc_user_purchase_local(request.user_id, flash_sale_id, request.product_id, qty)

    if background_tasks:
        background_tasks.add_task(_bg_log_order, new_order.order_id)
        background_tasks.add_task(_bg_notify_user, new_order.order_id, new_order.user_id)

    return new_order


def get_user_purchase_summary(
    db: Session,
    flash_sale_id: str,
    user_id: str,
    product_id: str,
) -> PurchaseTrackingResponse:
    sale = (
        db.query(FlashSale)
        .filter(FlashSale.flash_sale_id == flash_sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")

    orders = (
        db.query(FlashSaleOrder)
        .filter(
            FlashSaleOrder.flash_sale_id == flash_sale_id,
            FlashSaleOrder.user_id == user_id,
            FlashSaleOrder.product_id == product_id,
            FlashSaleOrder.status == "confirmed",
        )
        .order_by(FlashSaleOrder.purchase_timestamp.asc())
        .all()
    )

    purchases = [
        PurchaseEntry(
            order_id=o.order_id,
            quantity=o.quantity,
            timestamp=o.purchase_timestamp,
        )
        for o in orders
    ]

    total_purchased = sum(o.quantity for o in orders)

    fs_product = (
        db.query(FlashSaleProduct)
        .filter(
            FlashSaleProduct.flash_sale_id == flash_sale_id,
            FlashSaleProduct.product_id == product_id,
        )
        .first()
    )
    if not fs_product:
        raise HTTPException(
            status_code=404,
            detail="Product is not part of this flash sale",
        )

    limit_remaining = max(fs_product.max_per_user - total_purchased, 0)

    return PurchaseTrackingResponse(
        user_id=user_id,
        flash_sale_id=flash_sale_id,
        product_id=product_id,
        purchases=purchases,
        total_purchased=total_purchased,
        limit_remaining=limit_remaining,
    )

def get_remaining_limit(
    db: Session,
    flash_sale_id: str,
    user_id: str,
    product_id: str,
) -> RemainingLimitResponse:
    summary = get_user_purchase_summary(db, flash_sale_id, user_id, product_id)

    fs_product = (
        db.query(FlashSaleProduct)
        .filter(
            FlashSaleProduct.flash_sale_id == flash_sale_id,
            FlashSaleProduct.product_id == product_id,
        )
        .first()
    )
    max_per_user = fs_product.max_per_user

    return RemainingLimitResponse(
        user_id=summary.user_id,
        flash_sale_id=summary.flash_sale_id,
        product_id=summary.product_id,
        max_per_user=max_per_user,
        total_purchased=summary.total_purchased,
        limit_remaining=summary.limit_remaining,
    )

def verify_captcha(token: Optional[str]) -> bool:
    if not token:
        return False
    return True

def validate_purchase_request(
    db: Session,
    flash_sale_id: str,
    data: ValidatePurchaseRequest,
    client_ip: Optional[str] = None,
) -> ValidatePurchaseResponse:
    reasons: List[str] = []

    # 1. Check flash sale exists & active
    flash_sale = (
        db.query(FlashSale)
        .filter(FlashSale.flash_sale_id == flash_sale_id)
        .first()
    )
    if not flash_sale:
        return ValidatePurchaseResponse(
            allowed=False,
            reasons=["Flash sale not found"],
        )

    now = datetime.utcnow()
    if flash_sale.status != "active":
        reasons.append("Flash sale is not active")
    if not (flash_sale.start_time <= now <= flash_sale.end_time):
        reasons.append("Not within flash sale time window")

    # 2. Get flash sale product entry
    fs_product = (
        db.query(FlashSaleProduct)
        .filter(
            FlashSaleProduct.flash_sale_id == flash_sale.flash_sale_id,
            FlashSaleProduct.product_id == data.product_id,
        )
        .first()
    )
    if not fs_product:
        reasons.append("Product is not part of this flash sale")
        return ValidatePurchaseResponse(allowed=False, reasons=reasons)

    # 3. Per-user limit
    orders = (
        db.query(FlashSaleOrder)
        .filter(
            FlashSaleOrder.flash_sale_id == flash_sale.flash_sale_id,
            FlashSaleOrder.product_id == data.product_id,
            FlashSaleOrder.user_id == data.user_id,
            FlashSaleOrder.status == "confirmed",
        )
        .all()
    )
    total_prev = sum(o.quantity for o in orders)
    limit_remaining = max(fs_product.max_per_user - total_prev, 0)

    if data.quantity > limit_remaining:
        reasons.append("Per-user purchase limit exceeded")

    # 4. Cooling period – last purchase within 60 seconds
    if orders:
        last_order = max(orders, key=lambda o: o.purchase_timestamp)
        diff = now - last_order.purchase_timestamp
        if diff.total_seconds() < COOLING_PERIOD_SECONDS:
            reasons.append(
                f"Cooling period active. Please wait {COOLING_PERIOD_SECONDS - int(diff.total_seconds())} seconds"
            )

    # 5. Captcha validation
    if not verify_captcha(data.captcha_token):
        reasons.append("Captcha validation failed")

    # 6. IP-based tracking 
    if client_ip:
        other_users_same_ip = (
            db.query(FlashSaleOrder)
            .filter(
                FlashSaleOrder.flash_sale_id == flash_sale.flash_sale_id,
                FlashSaleOrder.product_id == data.product_id,
                FlashSaleOrder.client_ip == client_ip,
                FlashSaleOrder.user_id != data.user_id,
                FlashSaleOrder.status == "confirmed",
            )
            .count()
        )
        if other_users_same_ip >= 5:
            reasons.append(
                "Too many purchases from the same IP address. Possible abuse detected."
            )

    allowed = len(reasons) == 0

    return ValidatePurchaseResponse(
        allowed=allowed,
        reasons=reasons,
        limit_remaining=limit_remaining,
        cooling_required_seconds=COOLING_PERIOD_SECONDS if any(
            "Cooling period" in r for r in reasons
        ) else None,
    )

