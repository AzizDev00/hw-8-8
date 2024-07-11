from pydantic import BaseModel, EmailStr
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    is_staff: bool = False

class User(UserBase):
    id: int
    is_active: bool
    is_staff: bool

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    status: Optional[str] = "pending"

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int
    user: User
    product: Product

    class Config:
        orm_mode = True