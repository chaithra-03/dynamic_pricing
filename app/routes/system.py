from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.dependencies.auth import require_admin
from app.schemas.system import HealthCheckResponse, SystemMetricsResponse
from app.models.flash_sale import FlashSale
from app.models.flash_sale import FlashSaleOrder

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthCheckResponse)
def health_check(request: Request, db: Session = Depends(get_db)):
    """
    Lightweight public health check.
    Returns ok + DB connectivity check (SELECT 1).
    """
    now = datetime.utcnow()
    start_time = getattr(request.app.state, "start_time", now)
    uptime_seconds = (now - start_time).total_seconds()

    # DB quick check
    db_ok = True
    extra = {}
    try:
        # try a tiny query - SELECT 1
        db.execute(select(func.count()).select_from(func.sql.text('(SELECT 1)')))  # favor no table access
        # above is a safe lightweight attempt - some DBs may not like; fallback to select 1:
    except Exception:
        try:
            db.execute(select(1))
        except Exception as e:
            db_ok = False
            extra["db_error"] = str(e)

    # Optionally add presence of migrations table (if you want)
    try:
        q = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version';"
        ).fetchone()
        extra["alembic_version_table_present"] = bool(q)
    except Exception:
        # ignore
        pass

    status = "ok" if db_ok else "degraded"

    return HealthCheckResponse(
        status=status,
        now=now,
        uptime_seconds=uptime_seconds,
        db_ok=db_ok,
        extra=extra or None,
    )


@router.get("/metrics", response_model=SystemMetricsResponse, dependencies=[Depends(require_admin)])
def system_metrics(request: Request, db: Session = Depends(get_db)):
    """
    Admin-only system metrics in JSON form.
    Uses in-process counters stored on app.state.metrics and DB-derived metrics.
    """
    now = datetime.utcnow()
    start_time = getattr(request.app.state, "start_time", now)
    uptime_seconds = (now - start_time).total_seconds()

    metrics = getattr(request.app.state, "metrics", None) or {}
    requests_count = int(metrics.get("requests", 0))
    total_response_ms = float(metrics.get("total_response_ms", 0.0))
    avg_response_ms = (total_response_ms / requests_count) if requests_count > 0 else None
    cache_hits = int(metrics.get("cache_hits", 0)) if metrics.get("cache_hits") is not None else None
    cache_misses = int(metrics.get("cache_misses", 0)) if metrics.get("cache_misses") is not None else None
    cache_hit_rate = None
    if cache_hits is not None and cache_misses is not None:
        denom = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / denom) * 100.0 if denom > 0 else None

    # DB-derived metrics (simple examples)
    try:
        active_flash_sales = (
            db.query(func.count())
            .select_from(FlashSale)
            .filter(FlashSale.status == "active")
            .scalar()
        ) or 0
    except Exception:
        active_flash_sales = 0

    try:
        today = now.date()
        start_today = datetime.combine(today, datetime.min.time())
        # count orders today
        total_orders_today = (
            db.query(func.count())
            .select_from(FlashSaleOrder)
            .filter(FlashSaleOrder.purchase_timestamp >= start_today)
            .scalar()
        ) or 0

        total_orders = (
            db.query(func.count())
            .select_from(FlashSaleOrder)
            .scalar()
        ) or 0

        average_order_value = (
            db.query(func.avg(FlashSaleOrder.total_price))
            .select_from(FlashSaleOrder)
            .scalar()
        )
        if average_order_value is not None:
            average_order_value = float(average_order_value)
    except Exception:
        total_orders_today = 0
        total_orders = 0
        average_order_value = None

    return SystemMetricsResponse(
        uptime_seconds=uptime_seconds,
        now=now,
        requests_count=requests_count,
        avg_response_ms=avg_response_ms,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        cache_hit_rate=cache_hit_rate,
        active_flash_sales=int(active_flash_sales),
        total_orders_today=int(total_orders_today),
        total_orders=int(total_orders),
        average_order_value=average_order_value,
        extra=None,
    )