import asyncio
from fastapi import FastAPI
from app.database.connection import Base, engine
from app.routes.products import router as product_router
from app.routes.pricing.pricing_route import router as pricing_router
from app.routes.pricing.calculate_price import router as calculate_price_router
from app.routes.flash_sale import router as flash_sales_router
from app.routes.analytics import router as analytics_router  
from app.services.scheduler_service import (
    flash_sale_scheduler_loop,
    price_snapshot_scheduler_loop,
)
from app.routes.auth import router as auth_router

# Create all DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dynamic Pricing & Flash Sale Management System")

app.include_router(auth_router)
app.include_router(product_router)
app.include_router(pricing_router)
app.include_router(calculate_price_router)
app.include_router(flash_sales_router)
app.include_router(analytics_router)


@app.on_event("startup")
async def startup_event():
    # background loops
    asyncio.create_task(flash_sale_scheduler_loop())
    asyncio.create_task(price_snapshot_scheduler_loop())
