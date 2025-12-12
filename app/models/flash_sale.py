from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class FlashSale(Base):
    __tablename__ = "flash_sales"

    id = Column(Integer, primary_key=True, index=True)
    flash_sale_id = Column(String, unique=True, index=True)  # e.g. FLASH_001
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled", index=True)
    visibility = Column(String, default="public")  # public / private
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    visitors = Column(Integer, nullable=False, default=0)

    products = relationship(
        "FlashSaleProduct",
        back_populates="flash_sale",
        cascade="all, delete-orphan",
    )
    orders = relationship(
        "FlashSaleOrder",
        back_populates="flash_sale",
        cascade="all, delete-orphan",
    )


class FlashSaleProduct(Base):
    __tablename__ = "flash_sale_products"

    id = Column(Integer, primary_key=True, index=True)
    flash_sale_id = Column(
        String, ForeignKey("flash_sales.flash_sale_id"), nullable=False, index=True
    )
    product_id = Column(String, nullable=False, index=True)  # FK to products.product_id
    flash_sale_price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=False)
    discount_percentage = Column(Float, nullable=False)
    stock_allocated = Column(Integer, nullable=False)
    stock_remaining = Column(Integer, nullable=False)
    max_per_user = Column(Integer, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    flash_sale = relationship("FlashSale", back_populates="products")


class FlashSaleOrder(Base):
    __tablename__ = "flash_sale_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)  # e.g. ORD_001
    flash_sale_id = Column(
        String, ForeignKey("flash_sales.flash_sale_id"), nullable=False, index=True
    )
    product_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    flash_sale_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    savings = Column(Float, nullable=False)
    status = Column(String, default="confirmed")  
    payment_method = Column(String, nullable=True)
    client_ip = Column(String, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    purchase_timestamp = Column(DateTime, default=datetime.utcnow)
    flash_sale = relationship("FlashSale", back_populates="orders")
