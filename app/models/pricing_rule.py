from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime
from app.database.connection import Base


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String, unique=True, index=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    product_ids = Column(JSON, default=[])
    product_categories = Column(JSON, default=[])
    discount_type = Column(String)  # percentage, fixed, shipping
    discount_value = Column(Float)
    tiers = Column(JSON, default=[])
    user_tiers = Column(JSON, default=[])
    min_cart_value = Column(Float)
    schedule = Column(JSON, default={})
    priority = Column(Integer, default=10)
    status = Column(String, default="inactive")  # active/inactive
    is_exclusive = Column(Boolean, default=False)
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
