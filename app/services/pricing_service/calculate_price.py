from datetime import datetime, time
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.pricing_rule import PricingRule
from app.models.flash_sale import FlashSale, FlashSaleProduct


# ===================== PUBLIC ENTRY =====================


def calculate_final_price(
    db: Session,
    product: Product,
    quantity: int,
    user_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate final price with combined flash sale + dynamic pricing logic.

    Business rules:
    - Flash sale has highest priority.
    - Flash sale can apply partially if quantity > available stock or max_per_user.
    - Remaining quantity (if any) uses dynamic pricing rules.
    - Dynamic prices respect min_allowed_price, flash sale does NOT (by design choice).
    """

    base_price = float(product.base_price)
    min_price = float(product.min_allowed_price)

    # ---- 1) Check for applicable flash sale ----
    flash_row = _get_active_flash_sale_for_product(db, product)
    now = datetime.utcnow()

    flash_sale_applied = False
    flash_qty = 0
    dyn_qty = quantity

    flash_unit_price = 0.0
    flash_total_price = 0.0

    dynamic_unit_price = 0.0
    dynamic_total_price = 0.0
    dynamic_rules: List[PricingRule] = []

    flash_sale_info: Optional[Dict[str, Any]] = None

    if flash_row is not None:
        # Compute how many units can really go at flash sale price
        available_by_stock = max(int(flash_row.stock_remaining or 0), 0)
        if flash_row.max_per_user is not None:
            available_by_user = int(flash_row.max_per_user)
        else:
            available_by_user = quantity  # no per-user cap

        max_flash_units = min(quantity, available_by_stock, available_by_user)

        if max_flash_units > 0:
            flash_sale_applied = True
            flash_qty = max_flash_units
            dyn_qty = quantity - flash_qty

            flash_unit_price = float(flash_row.flash_sale_price)
            flash_total_price = flash_unit_price * flash_qty

            flash_sale_info = {
                "flash_sale_id": flash_row.flash_sale_id,
                "flash_sale_price": float(flash_row.flash_sale_price),
                "original_price": float(flash_row.original_price),
                "discount_percentage": float(flash_row.discount_percentage),
                "stock_remaining": int(flash_row.stock_remaining or 0),
                "max_per_user": flash_row.max_per_user,
                "status": "active",
                "start_time": flash_row.start_time,
                "end_time": flash_row.end_time,
            }

    # ---- 2) Dynamic pricing for remaining qty (if any) ----
    if dyn_qty > 0:
        dyn_unit_price, dynamic_rules = _calculate_dynamic_price(
            db=db,
            product=product,
            quantity=dyn_qty,
            user_tier=user_tier,
        )
        dynamic_unit_price = float(dyn_unit_price)
        dynamic_total_price = dynamic_unit_price * dyn_qty
    else:
        # No dynamic portion, still return a sensible number for unit price
        dynamic_unit_price = base_price
        dynamic_total_price = 0.0

    # ---- 3) Total combination ----
    total_final_price = flash_total_price + dynamic_total_price

    # Effective averaged unit price over the whole quantity
    unit_final_price = total_final_price / quantity if quantity > 0 else 0.0

    return {
        "base_price": base_price,
        "min_allowed_price": min_price,

        "flash_sale_applied": flash_sale_applied,
        "flash_sale_quantity": flash_qty,
        "dynamic_quantity": dyn_qty,

        "flash_sale_unit_price": flash_unit_price,
        "flash_sale_total_price": flash_total_price,

        "dynamic_unit_price": dynamic_unit_price,
        "dynamic_total_price": dynamic_total_price,

        "unit_final_price": unit_final_price,
        "total_final_price": total_final_price,

        "flash_sale": flash_sale_info,
        "applied_rules": dynamic_rules,
    }


# ===================== FLASH SALE LOOKUP =====================


def _get_active_flash_sale_for_product(db: Session, product: Product):
    """
    Return an active flash sale row for this product, or None.

    NOTE:
    - This does NOT enforce stock or user-limit; we do that in calculate_final_price().
    - We only care about active sales within time window.
    """
    now = datetime.utcnow()

    row = (
        db.query(
            FlashSaleProduct.flash_sale_id,
            FlashSaleProduct.flash_sale_price,
            FlashSaleProduct.original_price,
            FlashSaleProduct.discount_percentage,
            FlashSaleProduct.stock_remaining,
            FlashSaleProduct.max_per_user,
            FlashSale.start_time,
            FlashSale.end_time,
            FlashSale.status,
        )
        .join(FlashSale, FlashSaleProduct.flash_sale_id == FlashSale.flash_sale_id)
        .filter(
            FlashSaleProduct.product_id == product.product_id,
            FlashSale.status == "active",
            FlashSale.start_time <= now,
            FlashSale.end_time >= now,
        )
        .first()
    )

    return row


# ===================== DYNAMIC PRICING ENGINE =====================


def _get_applicable_rules(db: Session, product: Product) -> List[PricingRule]:
    """
    Return all active pricing rules that apply to this product via:
    - product_ids OR
    - product_categories
    """
    rules = db.query(PricingRule).filter(PricingRule.status == "active").all()
    applicable: List[PricingRule] = []

    for rule in rules:
        # If product_ids specified, product_id must be included
        if rule.product_ids:
            if product.product_id not in rule.product_ids:
                continue

        # If product_categories specified, category must match
        if rule.product_categories:
            if product.category not in rule.product_categories:
                continue

        applicable.append(rule)

    return applicable


def _calculate_dynamic_price(
    db: Session,
    product: Product,
    quantity: int,
    user_tier: Optional[str] = None,
) -> Tuple[float, List[PricingRule]]:
    """
    Apply dynamic pricing rules (NO flash sale) for the given quantity.

    Priority inside rules is handled by numeric 'priority' field:
    - lower priority value = higher precedence
    - exclusive rule stops further rule application

    Final price is clamped by min_allowed_price.
    """
    cart_value = float(product.base_price) * quantity
    active_rules = _get_applicable_rules(db, product)

    # Sort by priority, default 10 if missing
    sorted_rules = sorted(active_rules, key=lambda r: getattr(r, "priority", 10))

    price = float(product.base_price)
    applied_rules: List[PricingRule] = []

    for rule in sorted_rules:
        discount = _calculate_discount(
            rule=rule,
            quantity=quantity,
            user_tier=user_tier,
            cart_value=cart_value,
        )

        if discount and discount > 0:
            price = _apply_discount(price, discount)
            applied_rules.append(rule)

            if getattr(rule, "is_exclusive", False):
                break

    # Apply minimum allowed price floor
    price = max(price, float(product.min_allowed_price))
    return price, applied_rules


# ===================== DISCOUNT HELPERS =====================


def _calculate_discount(
    rule: PricingRule,
    quantity: int,
    user_tier: Optional[str] = None,
    cart_value: float = 0.0,
) -> float:
    """
    Return discount percentage (e.g. 10.0 = 10%).
    """

    # ---- 1) Time-Based Pricing ----
    if rule.type == "time_based":
        now = datetime.utcnow()

        # Valid from/until
        if rule.valid_from and now < rule.valid_from:
            return 0.0
        if rule.valid_until and now > rule.valid_until:
            return 0.0

        schedule = rule.schedule or {}
        days_of_week = schedule.get("days_of_week") or []
        start_time_str = schedule.get("start_time") or "00:00:00"
        end_time_str = schedule.get("end_time") or "23:59:59"

        # Day-of-week check
        if days_of_week:
            weekday_name = now.strftime("%A")  # "Monday", "Tuesday", ...
            if weekday_name not in days_of_week:
                return 0.0

        # Time-of-day check
        try:
            s_parts = [int(p) for p in start_time_str.split(":")]
            e_parts = [int(p) for p in end_time_str.split(":")]
            start_t = time(*s_parts)
            end_t = time(*e_parts)

            if not (start_t <= now.time() <= end_t):
                return 0.0
        except Exception:
            # If schedule time parsing fails, ignore intra-day limits
            pass

        if rule.discount_type == "percentage":
            return float(rule.discount_value or 0.0)
        return 0.0

    # ---- 2) Quantity-Based Pricing ----
    if rule.type == "quantity_based":
        for tier in rule.tiers or []:
            min_q = tier.get("min_quantity")
            max_q = tier.get("max_quantity")

            if min_q is None:
                continue
            if quantity < min_q:
                continue
            if max_q is not None and quantity > max_q:
                continue

            return float(tier.get("discount_percentage") or 0.0)
        return 0.0

    # ---- 3) User-Tier-Based Pricing ----
    if rule.type == "user_tier":
        # rule.user_tiers like ["gold", "platinum"]
        if user_tier and user_tier in (rule.user_tiers or []):
            return float(rule.discount_value or 0.0)
        return 0.0

    # ---- 4) Cart Threshold ----
    if rule.type == "cart_threshold":
        if cart_value >= (rule.min_cart_value or 0.0):
            # treating discount_value as percentage
            return float(rule.discount_value or 0.0)
        return 0.0

    return 0.0


def _apply_discount(price: float, discount_percentage: float) -> float:
    """
    Apply percentage discount:
    price=100, discount_percentage=10 -> 90
    """
    return price * (1.0 - discount_percentage / 100.0)
