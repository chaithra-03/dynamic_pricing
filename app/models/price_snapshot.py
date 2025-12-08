from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON

from app.database.connection import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    # e.g. ["RULE_001", "RULE_003"]
    active_rules = Column(JSON, default=[])
