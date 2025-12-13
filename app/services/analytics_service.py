from datetime import date, datetime
from typing import List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from fastapi import HTTPException
from app.models.flash_sale import FlashSale, FlashSaleOrder, FlashSaleProduct
from app.models.product import Product
from app.models.price_snapshot import PriceSnapshot
from app.schemas.analytics import (
    FlashSaleAnalyticsResponse,
    FlashSaleMetrics,
    PriceElasticityResponse,
    PriceElasticityAnalysis,
    RevenueByDayResponse,
    RevenueByDayItem,
)


# ---------- FLASH SALE ANALYTICS ----------

def get_flash_sale_analytics(db: Session, flash_sale_id: str) -> FlashSaleAnalyticsResponse:
    sale: FlashSale = (
        db.query(FlashSale)
        .filter(FlashSale.flash_sale_id == flash_sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")

    visitors = getattr(sale, "visitors", 0) or 0

    orders: List[FlashSaleOrder] = (
        db.query(FlashSaleOrder)
        .filter(
            FlashSaleOrder.flash_sale_id == flash_sale_id,
            FlashSaleOrder.status == "confirmed",
        )
        .all()
    )

    if not orders:
        if visitors > 0:
            conversion_rate = 0.0
        else:
            conversion_rate = 0.0  

        metrics = FlashSaleMetrics(
            total_revenue=0.0,
            units_sold=0,
            unique_buyers=0,
            conversion_rate=conversion_rate,
            average_order_value=0.0,
            stock_sell_through_rate=0.0,
            peak_hour=None,
            geographic_distribution={},
        )
        return FlashSaleAnalyticsResponse(flash_sale_id=flash_sale_id, metrics=metrics)

    total_revenue = sum(o.total_price for o in orders)
    units_sold = sum(o.quantity for o in orders)
    unique_buyers = len({o.user_id for o in orders})
    average_order_value = total_revenue / len(orders)

    fs_products: List[FlashSaleProduct] = (
        db.query(FlashSaleProduct)
        .filter(FlashSaleProduct.flash_sale_id == flash_sale_id)
        .all()
    )
    total_allocated = sum(p.stock_allocated for p in fs_products) or 1
    stock_sell_through_rate = (units_sold / total_allocated) * 100.0

    hour_buckets = defaultdict(int)
    for o in orders:
        h = o.purchase_timestamp.replace(minute=0, second=0, microsecond=0)
        hour_buckets[h] += o.quantity

    if hour_buckets:
        peak_dt = max(hour_buckets, key=lambda k: hour_buckets[k])
        peak_hour_str = peak_dt.strftime("%H:00-%H:59")
    else:
        peak_hour_str = None

    if visitors > 0:
        conversion_rate = (unique_buyers / visitors) * 100.0
    else:
        conversion_rate = 0.0

    geo_distribution = {}

    metrics = FlashSaleMetrics(
        total_revenue=total_revenue,
        units_sold=units_sold,
        unique_buyers=unique_buyers,
        conversion_rate=conversion_rate,
        average_order_value=average_order_value,
        stock_sell_through_rate=stock_sell_through_rate,
        peak_hour=peak_hour_str,
        geographic_distribution=geo_distribution,
    )

    return FlashSaleAnalyticsResponse(
        flash_sale_id=flash_sale_id,
        metrics=metrics,
    )
# ---------- PRICE ELASTICITY ----------

def get_price_elasticity(db: Session, product_id: str) -> PriceElasticityResponse:
    product = (
        db.query(Product)
        .filter(Product.product_id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    orders: List[FlashSaleOrder] = (
        db.query(FlashSaleOrder)
        .filter(
            FlashSaleOrder.product_id == product_id,
            FlashSaleOrder.status == "confirmed",
        )
        .all()
    )

    if not orders:
        analysis = PriceElasticityAnalysis(
            base_price=product.base_price,
            average_sale_price=product.current_price,
            sales_at_full_price=0,
            sales_at_discount=0,
            optimal_price_point=None,
            elasticity_coefficient=None,
        )
        return PriceElasticityResponse(product_id=product_id, analysis=analysis)

    base_price = product.base_price
    average_sale_price = sum(o.flash_sale_price for o in orders) / len(orders)

    sales_at_full_price = sum(
        o.quantity for o in orders if abs(o.flash_sale_price - base_price) < 1e-6
    )
    sales_at_discount = sum(
        o.quantity for o in orders if o.flash_sale_price < base_price - 1e-6
    )

    if sales_at_discount > 0 and sales_at_full_price > 0:
        q1 = sales_at_full_price
        q2 = sales_at_discount
        p1 = base_price
        p2 = average_sale_price

        if p1 != p2 and q1 != q2:
            dq = q2 - q1
            dp = p2 - p1
            q_avg = (q1 + q2) / 2
            p_avg = (p1 + p2) / 2
            elasticity = (dq / q_avg) / (dp / p_avg)
        else:
            elasticity = 0.0
    else:
        elasticity = 0.0

    optimal_price_point = (base_price + average_sale_price) / 2.0

    analysis = PriceElasticityAnalysis(
        base_price=base_price,
        average_sale_price=average_sale_price,
        sales_at_full_price=sales_at_full_price,
        sales_at_discount=sales_at_discount,
        optimal_price_point=optimal_price_point,
        elasticity_coefficient=elasticity,
    )

    return PriceElasticityResponse(product_id=product_id, analysis=analysis)


# ---------- REVENUE BY DAY ----------

def get_revenue_by_day(db: Session) -> RevenueByDayResponse:
    rows = (
        db.query(
            func.date(FlashSaleOrder.purchase_timestamp).label("day_str"),
            func.sum(FlashSaleOrder.total_price).label("revenue"),
        )
        .filter(FlashSaleOrder.status == "confirmed")
        .group_by(func.date(FlashSaleOrder.purchase_timestamp))
        .order_by("day_str")
        .all()
    )

    items: list[RevenueByDayItem] = []

    for row in rows:
        day_str = row.day_str
        revenue = row.revenue or 0

        if isinstance(day_str, str):
            d = date.fromisoformat(day_str)
        else:
            d = day_str.date() if hasattr(day_str, "date") else day_str

        items.append(
            RevenueByDayItem(
                date=d,
                revenue=float(revenue),
            )
        )

    return RevenueByDayResponse(items=items)
