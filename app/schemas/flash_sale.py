from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Product item inside a flash sale ----------

class FlashSaleProductItemBase(BaseModel):
    product_id: str
    flash_sale_price: float
    stock_allocated: int
    max_per_user: int
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None


class FlashSaleProductItemCreate(FlashSaleProductItemBase):
    pass


class FlashSaleProductItemResponse(FlashSaleProductItemBase):
    id: int
    stock_remaining: int

    class Config:
        orm_mode = True


# ---------- Flash sale main schemas ----------

class FlashSaleBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    visibility: str = "public"
    status: Optional[str] = "scheduled"


class FlashSaleCreate(FlashSaleBase):
    flash_sale_id: str    
    products: List[FlashSaleProductItemCreate]


class FlashSaleResponse(FlashSaleBase):
    flash_sale_id: str
    created_at: datetime
    updated_at: datetime
    products: List[FlashSaleProductItemResponse] = []

    class Config:
        orm_mode = True


# ---------- Purchase schemas ----------

class FlashSalePurchaseRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int = Field(gt=0)
    payment_method: str
    device_fingerprint: Optional[str] = None
    captcha_token: Optional[str] = None  

class FlashSalePurchaseResponse(BaseModel):
    order_id: str
    flash_sale_id: str
    product_id: str
    quantity: int
    flash_sale_price: float
    savings: float
    status: str
    purchase_timestamp: datetime

    class Config:
        orm_mode = True

class PurchaseEntry(BaseModel):
    order_id: str
    quantity: int
    timestamp: datetime

    class Config:
        orm_mode = True


class PurchaseTrackingResponse(BaseModel):
    user_id: str
    flash_sale_id: str
    product_id: str
    purchases: List[PurchaseEntry]
    total_purchased: int
    limit_remaining: int

    class Config:
        orm_mode = True
       
class RemainingLimitResponse(BaseModel):
    user_id: str
    flash_sale_id: str
    product_id: str
    max_per_user: int
    total_purchased: int
    limit_remaining: int

class ValidatePurchaseRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int = Field(gt=0)
    device_fingerprint: Optional[str] = None
    captcha_token: Optional[str] = None


class ValidatePurchaseResponse(BaseModel):
    allowed: bool
    reasons: List[str] = []
    limit_remaining: Optional[int] = None
    cooling_required_seconds: Optional[int] = None

