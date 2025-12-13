import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal  # or your session maker
from app.models.flash_sale import FlashSale, FlashSaleProduct, FlashSaleOrder
from app.models.product import Product
from app.models.price_snapshot import PriceSnapshot
from app.models.pricing_rule import PricingRule
from app.services.flash_sale import activate_flash_sale, end_flash_sale


def get_db_session() -> Session:
    return SessionLocal()


# ---------- FLASH SALE SCHEDULER ----------

async def flash_sale_scheduler_loop():
    """
    Loop that runs flash_sale_scheduler every 60 seconds.
    """
    while True:
        try:
            await flash_sale_scheduler()
        except Exception as e:
            # In real app, log this
            print(f"[flash_sale_scheduler_loop] Error: {e}")
        await asyncio.sleep(60)  # 1 minute


async def flash_sale_scheduler():
    """
    Runs every minute to activate/end flash sales based on time.
    """
    db = get_db_session()
    try:
        current_time = datetime.utcnow()

        # Activate scheduled sales
        scheduled_sales: List[FlashSale] = (
            db.query(FlashSale)
            .filter(FlashSale.status == "scheduled")
            .all()
        )
        for sale in scheduled_sales:
            if sale.start_time <= current_time <= sale.end_time:
                activate_flash_sale(db, sale.flash_sale_id)

        # End active sales
        active_sales: List[FlashSale] = (
            db.query(FlashSale)
            .filter(FlashSale.status == "active")
            .all()
        )
        for sale in active_sales:
            if sale.end_time <= current_time:
                end_flash_sale(db, sale.flash_sale_id)

    finally:
        db.close()


# ---------- PRICE SNAPSHOT SCHEDULER ----------

async def price_snapshot_scheduler_loop():
    """
    Loop that runs capture_price_snapshots every 1 hour.
    """
    while True:
        try:
            await capture_price_snapshots()
        except Exception as e:
            print(f"[price_snapshot_scheduler_loop] Error: {e}")
        await asyncio.sleep(60 * 60)  


async def capture_price_snapshots():
    """
    Captures hourly price snapshots for analytics.
    """
    db = get_db_session()
    try:
        products: List[Product] = db.query(Product).all()

        for product in products:
            active_rules = (
                db.query(PricingRule)
                .filter(PricingRule.status == "active")
                .all()
            )

            active_rule_ids = []
            for rule in active_rules:
                if rule.product_ids and product.product_id not in rule.product_ids:
                    continue
                if rule.product_categories and product.category not in rule.product_categories:
                    continue
                active_rule_ids.append(rule.rule_id)

            snapshot = PriceSnapshot(
                product_id=product.product_id,
                price=product.current_price,
                timestamp=datetime.utcnow(),
                active_rules=active_rule_ids,
            )
            db.add(snapshot)

        db.commit()
    finally:
        db.close()
