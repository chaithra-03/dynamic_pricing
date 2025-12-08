from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class ScheduleSchema(BaseModel):
    days_of_week: Optional[List[str]] = []
    start_time: Optional[str] = "00:00:00"
    end_time: Optional[str] = "23:59:59"

class TierSchema(BaseModel):
    min_quantity: int
    max_quantity: Optional[int] = None
    discount_percentage: float

class PricingRuleBase(BaseModel):
    rule_id: str
    type: str
    name: str
    product_ids: Optional[List[str]] = []
    product_categories: Optional[List[str]] = []
    discount_type: Optional[str]
    discount_value: Optional[float]
    tiers: Optional[List[TierSchema]] = []
    user_tiers: Optional[List[str]] = []
    min_cart_value: Optional[float]
    schedule: Optional[ScheduleSchema] = ScheduleSchema()
    priority: Optional[int] = 10
    status: Optional[str] = "inactive"
    is_exclusive: Optional[bool] = False
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]

class PricingRuleCreate(PricingRuleBase):
    pass

class PricingRuleUpdate(PricingRuleBase):
    pass

class PricingRuleResponse(PricingRuleBase):
    id: int

    class Config:
        orm_mode = True
