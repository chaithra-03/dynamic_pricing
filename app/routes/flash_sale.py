from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request,BackgroundTasks
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.flash_sale import (
    FlashSaleCreate,
    FlashSaleResponse,
    FlashSalePurchaseRequest,
    FlashSalePurchaseResponse,
    PurchaseTrackingResponse,
    RemainingLimitResponse,
    ValidatePurchaseRequest,
    ValidatePurchaseResponse,
)
from app.services.flash_sale import (
    create_flash_sale,
    list_flash_sales,
    get_flash_sale,
    activate_flash_sale,
    cancel_flash_sale,
    end_flash_sale,
    purchase_in_flash_sale,
    get_user_purchase_summary,
    get_remaining_limit,
    validate_purchase_request,
)
from app.dependencies.auth import require_auth, require_admin

router = APIRouter(prefix="/flash-sales", tags=["Flash Sales"])


# ---------- CREATE FLASH SALE ----------

@router.post("/", response_model=FlashSaleResponse, dependencies=[Depends(require_admin)])
def create_flash_sale_route(
    data: FlashSaleCreate,
    db: Session = Depends(get_db),
):
    flash_sale = create_flash_sale(db, data)
    return flash_sale


# ---------- LIST FLASH SALES ----------

@router.get("/", response_model=List[FlashSaleResponse])
def list_flash_sales_route(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_flash_sales(db, status=status)


# ---------- GET SINGLE FLASH SALE ----------

@router.get("/{flash_sale_id}", response_model=FlashSaleResponse)
def get_flash_sale_route(
    flash_sale_id: str,
    db: Session = Depends(get_db),
):
    flash_sale = get_flash_sale(db, flash_sale_id)
    if not flash_sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")
    return flash_sale


# ---------- ACTIVATE FLASH SALE ----------

@router.post("/{flash_sale_id}/activate", response_model=FlashSaleResponse, dependencies=[Depends(require_admin)])
def activate_flash_sale_route(
    flash_sale_id: str,
    db: Session = Depends(get_db),
):
    flash_sale = activate_flash_sale(db, flash_sale_id)
    if not flash_sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")
    return flash_sale


# ---------- END FLASH SALE (OPTIONAL) ----------

@router.post("/{flash_sale_id}/end", response_model=FlashSaleResponse, dependencies=[Depends(require_admin)])
def end_flash_sale_route(
    flash_sale_id: str,
    db: Session = Depends(get_db),
):
    flash_sale = end_flash_sale(db, flash_sale_id)
    if not flash_sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")
    return flash_sale


# ---------- CANCEL FLASH SALE ----------

@router.post("/{flash_sale_id}/cancel", response_model=FlashSaleResponse, dependencies=[Depends(require_admin)])
def cancel_flash_sale_route(
    flash_sale_id: str,
    db: Session = Depends(get_db),
):
    flash_sale = cancel_flash_sale(db, flash_sale_id)
    if not flash_sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")
    return flash_sale


# ---------- PURCHASE DURING FLASH SALE ----------
@router.post(
    "/{flash_sale_id}/purchase",
    response_model=FlashSalePurchaseResponse,
    dependencies=[Depends(require_auth)],
)
def purchase_flash_sale_route(
    flash_sale_id: str,
    request_body: FlashSalePurchaseRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    order = purchase_in_flash_sale(
        db=db,
        flash_sale_id=flash_sale_id,
        request=request_body,
        client_ip=client_ip,
        background_tasks=background_tasks,
    )
    return order


@router.get(
    "/{flash_sale_id}/my-purchases",
    response_model=PurchaseTrackingResponse,
    dependencies=[Depends(require_auth)]
)
def my_purchases_route(
    flash_sale_id: str,
    user_id: str,
    product_id: str,
    db: Session = Depends(get_db),
):
    """
    User's purchase history for a product in a flash sale.
    """
    return get_user_purchase_summary(db, flash_sale_id, user_id, product_id)

@router.get(
    "/{flash_sale_id}/remaining-limit",
    response_model=RemainingLimitResponse,
    dependencies=[Depends(require_auth)]
)
def remaining_limit_route(
    flash_sale_id: str,
    user_id: str,
    product_id: str,
    db: Session = Depends(get_db),
):
    """
    Check the remaining purchase limit for a user & product.
    """
    return get_remaining_limit(db, flash_sale_id, user_id, product_id)

@router.post(
    "/{flash_sale_id}/validate-purchase",
    response_model=ValidatePurchaseResponse,
    dependencies=[Depends(require_auth)]
)
def validate_purchase_route(
    flash_sale_id: str,
    body: ValidatePurchaseRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Pre-purchase validation:
    - per-user limit
    - cooling period
    - captcha
    - basic IP-based checks
    """
    client_ip = request.client.host if request.client else None
    return validate_purchase_request(
        db=db,
        flash_sale_id=flash_sale_id,
        data=body,
        client_ip=client_ip,
    )



