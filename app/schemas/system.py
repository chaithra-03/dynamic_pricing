from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class HealthCheckResponse(BaseModel):
    status: str
    now: datetime
    uptime_seconds: float
    db_ok: bool
    extra: Optional[Dict[str, Any]] = None


class SystemMetricsResponse(BaseModel):
    uptime_seconds: float
    now: datetime

    # middleware counters
    requests_count: int
    avg_response_ms: Optional[float] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    cache_hit_rate: Optional[float] = None

    # DB metrics
    active_flash_sales: int
    total_orders_today: int
    total_orders: int
    average_order_value: Optional[float] = None

    # optional arbitrary metrics map
    extra: Optional[Dict[str, Any]] = None