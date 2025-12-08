from sqlalchemy import Column, String, Float, Integer, DateTime
from datetime import datetime
from app.database.connection import Base

class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    
    base_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    min_allowed_price = Column(Float, nullable=False)
    
    currency = Column(String, default="USD")
    stock_quantity = Column(Integer, default=0)
    pricing_tier = Column(String, default="standard")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
