from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.schemas.product import ProductCreate, ProductUpdate, BulkPriceUpdateRequest
from typing import List, Tuple
from sqlalchemy import func

def record_price_change(
    db: Session,
    product_id: str,
    price_type: str,
    old_price: float,
    new_price: float
):
    history = PriceHistory(
        product_id=product_id,
        price_type=price_type,
        old_price=old_price,
        new_price=new_price
    )
    db.add(history)


# --------------------------
# CREATE PRODUCT
# --------------------------
def create_product(db: Session, data: ProductCreate):
    product = Product(**data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

# --------------------------
# GET PRODUCT
# --------------------------
def get_product(db: Session, product_id: str):
    return db.query(Product).filter(Product.product_id == product_id).first()

# --------------------------
# LIST PRODUCTS
# --------------------------
def list_products(db: Session):
    return db.query(Product).all()

# --------------------------
# UPDATE PRODUCT
# --------------------------
def update_product(db: Session, product_id: str, data: ProductUpdate):
    product = get_product(db, product_id)
    if not product:
        return None

    price_fields = ["base_price", "current_price", "cost_price", "min_allowed_price"]

    for key, value in data.dict().items():
        if hasattr(product, key):
            old_val = getattr(product, key)

            if key in price_fields and old_val != value:
                record_price_change(db, product_id, key, old_val, value)

            setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


# --------------------------
# DELETE PRODUCT
# --------------------------
def delete_product(db: Session, product_id: str):
    product = get_product(db, product_id)
    if not product:
        return False

    db.delete(product)
    db.commit()
    return True

# --------------------------
# UPDATE BASE PRICE + HISTORY
# --------------------------
def update_base_price(
    db: Session,
    product_id: str,
    new_base_price: float,
    sync_current_price: bool = False
):
    product = get_product(db, product_id)
    if not product:
        return None

    final_base_price = max(new_base_price, product.min_allowed_price)

    record_price_change(
        db, product_id,
        price_type="base_price",
        old_price=product.base_price,
        new_price=final_base_price
    )
    product.base_price = final_base_price

    if sync_current_price:
        final_current_price = max(final_base_price, product.min_allowed_price)

        if final_current_price != product.current_price:
            record_price_change(
                db, product_id,
                price_type="current_price",
                old_price=product.current_price,
                new_price=final_current_price
            )
            product.current_price = final_current_price

    db.commit()
    db.refresh(product)
    return product

# --------------------------
# GET PRICE HISTORY
# --------------------------
def get_price_history(
    db: Session,
    product_id: str,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[PriceHistory], int]:
    """
    Returns (items, total_count)
    page is 1-based.
    """
    if page < 1:
        page = 1
    MAX_PAGE_SIZE = 200
    if page_size < 1:
        page_size = 1
    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE

    query = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)

    total = query.with_entities(func.count()).scalar() or 0

    offset = (page - 1) * page_size
    items = (
        query
        .order_by(PriceHistory.changed_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return items, total

# --------------------------
# BULK PRICE UPDATE
# --------------------------
def bulk_update_prices(db: Session, request: BulkPriceUpdateRequest):
    results = []

    for item in request.data:
        product = get_product(db, item.product_id)

        if not product:
            results.append({
                "product_id": item.product_id,
                "status": "not_found"
            })
            continue

        old_price = product.current_price

        applied_price = max(item.new_price, product.min_allowed_price)

        if applied_price != old_price:
            record_price_change(
                db,
                item.product_id,
                price_type="current_price",
                old_price=old_price,
                new_price=applied_price
            )

        product.current_price = applied_price

        results.append({
            "product_id": item.product_id,
            "status": "updated",
            "old_price": old_price,
            "requested_price": item.new_price,
            "final_applied_price": applied_price,
            "note": "Price adjusted to min_allowed_price"
                    if applied_price != item.new_price else "OK"
        })

    db.commit()
    return results
