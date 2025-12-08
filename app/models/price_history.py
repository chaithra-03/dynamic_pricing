from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database.connection import Base

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True)
    price_type = Column(String)
    old_price = Column(Float)
    new_price = Column(Float)
    changed_at = Column(DateTime, default=datetime.utcnow)
