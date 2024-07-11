from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    reset_token = Column(String, nullable=True, index=True)
    orders = relationship("Order", back_populates="user")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, index=True)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="orders")
    product_id = Column(Integer, ForeignKey('products.id'))
    product = relationship("Product")
    quantity = Column(Integer, nullable=False)
    status = Column(String, default="pending")
