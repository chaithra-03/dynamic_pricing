from typing import Optional
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.product_service import get_product
from app.services.pricing_service.calculate_price import calculate_final_price
from app.dependencies.auth import require_auth
from app.enums.user_tiers import UserTier

router = APIRouter(tags=["Pricing & Calculation"])


@router.get(
    "/products/{product_id}/calculate-price",
    dependencies=[Depends(require_auth)],
)
def calculate_price(
    product_id: str,
    quantity: int = 1,
    user_tier: Optional[UserTier] = None,
    db: Session = Depends(get_db),
):
    """
    Calculate final price based on priority:

    1. Flash Sale
    2. User Tier Based
    3. Quantity Based
    4. Time Based
    5. Base Price
    """

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    user_tier_value: Optional[str] = user_tier.value if user_tier else None

    # ---- measure calculation time ----
    start = perf_counter()
    result = calculate_final_price(
        db=db,
        product=product,
        quantity=quantity,
        user_tier=user_tier_value,
    )
    duration_ms = (perf_counter() - start) * 1000.0

    # optional logging if slower than target
    if duration_ms > 30.0:
        print(
            f"[WARN] Price calculation for product {product_id} took "
            f"{duration_ms:.2f} ms (quantity={quantity})"
        )

    flash_qty = result["flash_sale_quantity"]
    dyn_qty = result["dynamic_quantity"]

    # ---------- Human-readable message ----------
    if result["flash_sale_applied"] and dyn_qty > 0:
        message = (
            f"Flash sale applied for available quantity ({flash_qty}). "
            f"Remaining {dyn_qty} units priced using dynamic pricing rules."
        )
    elif result["flash_sale_applied"]:
        message = f"Flash sale applied for all units ({flash_qty})."
    else:
        message = "Dynamic pricing applied. No active flash sale."

    # ---------- Structured breakdown per segment ----------
    pricing_breakdown = []

    if flash_qty > 0:
        pricing_breakdown.append(
            {
                "label": f"Flash sale applied for {flash_qty} units",
                "quantity": flash_qty,
                "unit_price": result["flash_sale_unit_price"],
                "total_price": result["flash_sale_total_price"],
                "flash_sale_id": (
                    result["flash_sale"]["flash_sale_id"]
                    if result["flash_sale"] is not None
                    else None
                ),
            }
        )

    if dyn_qty > 0:
        pricing_breakdown.append(
            {
                "label": f"Dynamic pricing for remaining {dyn_qty} units",
                "quantity": dyn_qty,
                "unit_price": result["dynamic_unit_price"],
                "total_price": result["dynamic_total_price"],
                "applied_rules": [rule.rule_id for rule in result["applied_rules"]],
            }
        )

    # ---------- Explicit summary for each part + grand total ----------
    summary = {
        "flash_sale": {
            "quantity": flash_qty,
            "total_price": result["flash_sale_total_price"],
        },
        "dynamic_pricing": {
            "quantity": dyn_qty,
            "total_price": result["dynamic_total_price"],
        },
        "grand_total": {
            "quantity": quantity,
            "total_price": result["total_final_price"],
            "effective_unit_price": result["unit_final_price"],
        },
    }

    # ---------- Final response ----------
    return {
        "message": message,
        "product_id": product.product_id,
        "name": product.name,
        "category": product.category,
        "currency": product.currency,
        "quantity_requested": quantity,
        "flash_sale_quantity": flash_qty,
        "dynamic_quantity": dyn_qty,
        "user_tier": user_tier_value,

        "base_price": result["base_price"],
        "min_allowed_price": result["min_allowed_price"],

        "unit_final_price": result["unit_final_price"],
        "total_final_price": result["total_final_price"],

        "flash_sale_applied": result["flash_sale_applied"],
        "flash_sale_unit_price": result["flash_sale_unit_price"],
        "flash_sale_total_price": result["flash_sale_total_price"],

        "dynamic_unit_price": result["dynamic_unit_price"],
        "dynamic_total_price": result["dynamic_total_price"],

        "flash_sale": result["flash_sale"],
        "applied_discount_rules": [rule.rule_id for rule in result["applied_rules"]],
        "pricing_breakdown": pricing_breakdown,
        "summary": summary,

        "calculated_in_ms": duration_ms,
    }
