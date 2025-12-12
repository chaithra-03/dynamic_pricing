from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class PriceHistoryResponse(BaseModel):
    id: int
    product_id: str
    price_type: str
    old_price: float
    new_price: float
    changed_at: datetime

    class Config:
        orm_mode = True

class PriceHistoryPageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int

class PriceHistoryPageResponse(BaseModel):
    items: List[PriceHistoryResponse]
    meta: PriceHistoryPageMeta