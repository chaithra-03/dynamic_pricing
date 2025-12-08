from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.product import BulkPriceUpdateRequest, ProductCreate, ProductUpdate, ProductResponse
from app.schemas.price_history import PriceHistoryResponse
from app.services.product_service import (
    create_product, get_product, list_products,
    update_product, delete_product, update_base_price,
    get_price_history, bulk_update_prices
)
from app.dependencies.auth import require_auth, require_admin
from app.models.user import User


router = APIRouter(prefix="/products", tags=["Product & Base Pricing Management"])

# CREATE
@router.post("/", response_model=ProductResponse, dependencies=[Depends(require_admin)])
def create(data: ProductCreate, db: Session = Depends(get_db)):
    return create_product(db, data)

# LIST
@router.get("/", response_model=list[ProductResponse])
def list_all(db: Session = Depends(get_db)):
    return list_products(db)

# GET BY ID
@router.get("/{product_id}", response_model=ProductResponse)
def get(product_id: str, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product

# UPDATE
@router.put("/{product_id}", response_model=ProductResponse, dependencies=[Depends(require_admin)])
def update(product_id: str, data: ProductUpdate, db: Session = Depends(get_db)):
    product = update_product(db, product_id, data)
    if not product:
        raise HTTPException(404, "Product not found")
    return product

# DELETE
@router.delete("/{product_id}", dependencies=[Depends(require_admin)])
def delete(product_id: str, db: Session = Depends(get_db)):
    success = delete_product(db, product_id)
    if not success:
        raise HTTPException(404, "Product not found")
    return {"message": "Product deleted"}

# BASE PRICE UPDATE
@router.put("/{product_id}/base-price", response_model=ProductResponse, dependencies=[Depends(require_admin)])
def update_price(
    product_id: str,
    new_base_price: float,
    sync_current_price: bool = False,       
    db: Session = Depends(get_db)
):
    product = update_base_price(db, product_id, new_base_price, sync_current_price)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


# PRICE HISTORY
@router.get("/{product_id}/price-history", response_model=list[PriceHistoryResponse], dependencies=[Depends(require_admin)])
def view_history(product_id: str, db: Session = Depends(get_db)):
    return get_price_history(db, product_id)

# BULK UPDATE
@router.post("/bulk-price-update", dependencies=[Depends(require_admin)])
def bulk_update(request: BulkPriceUpdateRequest, db: Session = Depends(get_db)):
    return bulk_update_prices(db, request)