# tests/test_e2e_suite.py
from datetime import datetime, timedelta
import uuid
import pytest

from fastapi import HTTPException

# services & schemas
from app.services.product_service import create_product, get_product
from app.services.pricing_service.calculate_price import calculate_final_price
from app.services.flash_sale import (
    purchase_in_flash_sale,
)
from app.routes.products import create  # optional route-level import if needed
from app.routes.flash_sale import create_flash_sale_route  # route handler (calls service)
from app.schemas.product import ProductCreate
from app.schemas.flash_sale import FlashSalePurchaseRequest, FlashSaleCreate

# models (direct ORM usage)
from app.models.pricing_rule import PricingRule
from app.models.flash_sale import FlashSale, FlashSaleProduct
from app.database.connection import Base


# Lightweight request object for service calls where the route uses Request
class SimpleReq:
    def __init__(self, user_id, product_id, quantity, payment_method="card"):
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity
        self.payment_method = payment_method
        self.device_fingerprint = None
        self.captcha_token = "ok"


def _create_test_product(db, prod_id="TEST_E2E_PROD_001", base_price=200.0, stock=20):
    """
    Create and return a product using the product service.
    """
    payload = ProductCreate(
        product_id=prod_id,
        name="E2E Test Product",
        category="test",
        base_price=base_price,
        current_price=base_price,
        cost_price=base_price * 0.6,
        min_allowed_price=base_price * 0.5,
        currency="INR",
        stock_quantity=stock,
    )
    prod = create_product(db, payload)
    return prod


def _create_active_flash_and_product_entry(db, prod_id: str, fs_price: float, stock_alloc=5, max_per_user=2):
    """
    Insert a FlashSale and FlashSaleProduct (ORM) and return the flash_sale_id.
    """
    now = datetime.utcnow()
    fs_id = f"FLASH_TEST_{uuid.uuid4().hex[:6].upper()}"
    flash = FlashSale(
        flash_sale_id=fs_id,
        name="E2E Flash",
        description="created by test",
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(hours=1),
        status="active",
        visibility="public",
    )
    db.add(flash)
    db.flush()

    fs_product = FlashSaleProduct(
        flash_sale_id=fs_id,
        product_id=prod_id,
        flash_sale_price=fs_price,
        original_price=float(get_product(db, prod_id).current_price),
        discount_percentage=round((1 - fs_price / float(get_product(db, prod_id).current_price)) * 100, 2),
        stock_allocated=stock_alloc,
        stock_remaining=stock_alloc,
        max_per_user=max_per_user,
        version=1,
    )
    db.add(fs_product)
    db.commit()
    db.refresh(flash)
    return fs_id


@pytest.mark.order(1)
def test_create_product_service(db):
    """
    Create a product using the service and verify persisted values.
    """
    prod_id = f"PROD_E2E_{uuid.uuid4().hex[:6].upper()}"
    created = _create_test_product(db, prod_id=prod_id, base_price=250.0, stock=15)

    assert created is not None
    assert created.product_id == prod_id

    fetched = get_product(db, prod_id)
    assert fetched is not None
    assert float(fetched.base_price) == pytest.approx(250.0)
    assert fetched.stock_quantity == 15


@pytest.mark.order(2)
def test_create_pricing_rule_direct_orm(db):
    """
    Create a pricing rule directly (ORM) for a user-tier discount and verify existence.
    This test inserts a minimal rule record; adjust fields if your PricingRule model requires alternatives.
    """
    # depends on schema: ensure a product exists
    prod = _create_test_product(db, prod_id=f"PRULE_PROD_{uuid.uuid4().hex[:4].upper()}", base_price=120.0)

    rule = PricingRule(
        rule_id=f"RULE_{uuid.uuid4().hex[:8].upper()}",
        name="Test user-tier discount",
        type="user_tier",
        status="active",
        priority=10,
        discount_type="percentage",
        discount_value=10.0,  # 10% for the user tier
        user_tiers=["gold"],  # assume JSON/ARRAY-compatible column
        product_ids=[prod.product_id],  # assume JSON/ARRAY-compatible column
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    # reload to verify
    saved = db.query(PricingRule).filter(PricingRule.rule_id == rule.rule_id).first()
    assert saved is not None
    assert saved.type == "user_tier"
    assert float(saved.discount_value) == pytest.approx(10.0)


@pytest.mark.order(3)
def test_calculate_price_with_user_tier_rule(db):
    """
    Create a product and a user-tier rule then verify calculate_final_price applies the discount.
    """
    prod = _create_test_product(db, prod_id=f"PRC_PROD_{uuid.uuid4().hex[:4].upper()}", base_price=200.0)

    # create a user-tier rule via ORM (applies to product)
    rule = PricingRule(
        rule_id=f"RULE_{uuid.uuid4().hex[:8].upper()}",
        name="Gold tier 15% off",
        type="user_tier",
        status="active",
        priority=5,
        discount_type="percentage",
        discount_value=15.0,
        user_tiers=["gold"],
        product_ids=[prod.product_id],
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # calculate price for a gold user
    res = calculate_final_price(db=db, product=prod, quantity=2, user_tier="gold")

    # expected dynamic unit price = base_price * (1 - 0.15)
    expected_unit = float(prod.base_price) * (1.0 - 0.15)
    assert res["dynamic_unit_price"] == pytest.approx(expected_unit, rel=1e-3)
    assert res["unit_final_price"] == pytest.approx(expected_unit, rel=1e-3)


@pytest.mark.order(4)
def test_create_flash_sale_route_handler(db):
    """
    Test the create_flash_sale route handler by calling it directly.
    This avoids HTTP auth complexity and validates end-to-end route logic that calls the service.
    """
    prod = _create_test_product(db, prod_id=f"FS_PROD_{uuid.uuid4().hex[:4].upper()}", base_price=999.0)

    # Prepare flash sale create payload matching your schema
    now = datetime.utcnow()
    flash_payload = FlashSaleCreate(
        flash_sale_id=f"FLASH_ROUTE_{uuid.uuid4().hex[:6].upper()}",
        name="Route-created flash",
        description="test route",
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(hours=1),
        status="scheduled",
        visibility="public",
        products=[
            {
                "product_id": prod.product_id,
                "flash_sale_price": 499.0,
                "original_price": prod.current_price,
                "discount_percentage": round((1 - 499.0 / float(prod.current_price)) * 100, 2),
                "stock_allocated": 5,
                "max_per_user": 2,
            }
        ],
    )

    # call the route handler directly (it calls create_flash_sale service internally)
    created = create_flash_sale_route(flash_payload, db=db)
    assert created is not None
    assert hasattr(created, "flash_sale_id")
    assert created.flash_sale_id == flash_payload.flash_sale_id


@pytest.mark.order(5)
def test_purchase_flash_sale_service_flow(db):
    """
    Create a product + active flash sale and perform a purchase via the service.
    Validate order returned and that user's purchase summary reflects it.
    """
    prod = _create_test_product(db, prod_id=f"BUY_PROD_{uuid.uuid4().hex[:4].upper()}", base_price=1000.0, stock=10)

    # create active flash sale + product entry
    fs_id = _create_active_flash_and_product_entry(db, prod.product_id, fs_price=499.99, stock_alloc=3, max_per_user=2)

    # perform purchase (service)
    req = SimpleReq(user_id="buyer_e2e", product_id=prod.product_id, quantity=1)
    order = purchase_in_flash_sale(db=db, flash_sale_id=fs_id, request=req, client_ip="127.0.0.1")
    assert order is not None
    assert order.user_id == "buyer_e2e"
    assert order.quantity == 1

    # verify remaining stock in DB decreased by 1
    fs_product = db.query(FlashSaleProduct).filter(
        FlashSaleProduct.flash_sale_id == fs_id,
        FlashSaleProduct.product_id == prod.product_id
    ).first()
    assert fs_product.stock_remaining == fs_product.stock_allocated - 1
