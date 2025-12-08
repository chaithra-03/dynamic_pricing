from pydantic import BaseModel
from datetime import datetime

class PriceHistoryResponse(BaseModel):
    id: int
    product_id: str
    price_type: str
    old_price: float
    new_price: float
    changed_at: datetime

    class Config:
        orm_mode = True
