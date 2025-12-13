from datetime import datetime, date
from typing import Dict, Optional, List
from pydantic import BaseModel


# ---------- Flash sale analytics ----------

class FlashSaleMetrics(BaseModel):
    total_revenue: float
    units_sold: int
    unique_buyers: int
    conversion_rate: Optional[float] = None 
    average_order_value: float
    stock_sell_through_rate: float
    peak_hour: Optional[str] = None
    geographic_distribution: Dict[str, int] = {}


class FlashSaleAnalyticsResponse(BaseModel):
    flash_sale_id: str
    metrics: FlashSaleMetrics


# ---------- Price elasticity ----------

class PriceElasticityAnalysis(BaseModel):
    base_price: float
    average_sale_price: float
    sales_at_full_price: int
    sales_at_discount: int
    optimal_price_point: Optional[float] = None
    elasticity_coefficient: Optional[float] = None


class PriceElasticityResponse(BaseModel):
    product_id: str
    analysis: PriceElasticityAnalysis


# ---------- Revenue by day ----------

class RevenueByDayItem(BaseModel):
    date: date
    revenue: float


class RevenueByDayResponse(BaseModel):
    items: List[RevenueByDayItem]
