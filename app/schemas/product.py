from pydantic import BaseModel
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    category: str
    base_price: float
    current_price: float
    cost_price: float
    min_allowed_price: float
    currency: str = "USD"
    stock_quantity: int
    pricing_tier: str = "standard"

class ProductCreate(ProductBase):
    product_id: str

class ProductUpdate(ProductBase):
    pass

class ProductResponse(ProductBase):
    product_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class BulkPriceUpdateItem(BaseModel):
    product_id: str
    new_price: float


class BulkPriceUpdateRequest(BaseModel):
    data: list[BulkPriceUpdateItem]