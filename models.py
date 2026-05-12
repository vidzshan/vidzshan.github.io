# models.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    jan_code = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    features = Column(Text, default="")
    specs = Column(Text, default="")
    mercari_text = Column(Text, default="")
    image_folder = Column(String(200), default="")
    cainz_url = Column(String(300), default="")
    category = Column(String(100), default="Uncategorized")
    
    mercari_price = Column(Integer, default=0)
    expected_profit = Column(Integer, default=0)
    shipping_tier = Column(Integer, default=120)
    shipping_fee = Column(Integer, default=1200)
    mercari_status = Column(String(50), default="Not Listed")
    
    # 🚨 NEW: Timestamp to track data freshness
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    inventory_logs = relationship("InventoryLog", back_populates="product", cascade="all, delete-orphan")

class InventoryLog(Base):
    __tablename__ = 'inventory_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    jan_code = Column(String(50), ForeignKey('products.jan_code'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stock_quantity = Column(Integer, nullable=False)
    product = relationship("Product", back_populates="inventory_logs")

class TrackedJan(Base):
    __tablename__ = 'tracked_jans'
    jan_code = Column(String(50), primary_key=True)
    status = Column(String(100), nullable=False) 
    last_checked = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, default="")

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.sqlite')
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()