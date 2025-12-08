from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.analytics import (
    FlashSaleAnalyticsResponse,
    PriceElasticityResponse,
    RevenueByDayResponse,
)
from app.services.analytics_service import (
    get_flash_sale_analytics,
    get_price_elasticity,
    get_revenue_by_day,
)
from app.dependencies.auth import require_admin

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


@router.get("/flash-sales/{flash_sale_id}", response_model=FlashSaleAnalyticsResponse, dependencies=[Depends(require_admin)])
def flash_sale_analytics(
    flash_sale_id: str,
    db: Session = Depends(get_db),
):
    return get_flash_sale_analytics(db, flash_sale_id)


@router.get("/products/{product_id}/price-elasticity", response_model=PriceElasticityResponse, dependencies=[Depends(require_admin)])
def product_price_elasticity(
    product_id: str,
    db: Session = Depends(get_db),
):
    return get_price_elasticity(db, product_id)


@router.get("/reports/revenue-by-day", response_model=RevenueByDayResponse, dependencies=[Depends(require_admin)])
def revenue_by_day(
    db: Session = Depends(get_db),
):
    return get_revenue_by_day(db)
