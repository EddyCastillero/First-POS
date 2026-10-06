from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base 

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)