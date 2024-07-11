import logging
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import models, schemas, utils
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    try:
        return db.query(models.User).filter(models.User.username == username).first()
    except Exception as e:
        logging.error(f"Error getting user by username: {e}")
        return None

def get_user_by_email(db: Session, email: str):
    try:
        return db.query(models.User).filter(models.User.email == email).first()
    except Exception as e:
        logging.error(f"Error getting user by email: {e}")
        return None

def create_user(db: Session, user: schemas.UserCreate) -> Optional[models.User]:
    hashed_password = utils.get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password, is_staff=user.is_staff)
    try:
        logging.info(f"Attempting to create user: {user.username}")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logging.info(f"User created successfully: {db_user.username}")
        return db_user
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        db.rollback()
        return None


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username=username)
    if not user:
        return False
    if not utils.verify_password(password, user.hashed_password):
        return False
    return user

def create_reset_token(user: models.User):
    token_expires = timedelta(hours=1)
    reset_token = utils.create_access_token(data={"sub": user.email}, expires_delta=token_expires)
    user.reset_token = reset_token
    return reset_token

def reset_password(db: Session, token: str, new_password: str):
    try:
        payload = jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logging.error("Email not found in token payload")
            return False
        user = get_user_by_email(db, email=email)
        if user is None:
            logging.error(f"User not found for email: {email}")
            return False
        if user.reset_token != token:
            logging.error("Token mismatch")
            return False
        user.hashed_password = utils.get_password_hash(new_password)
        user.reset_token = None
        db.commit()
        db.refresh(user)
        logging.info(f"Password reset successful for user: {email}")
        return True
    except JWTError as e:
        logging.error(f"JWT error: {e}")
        return False
    except Exception as e:
        logging.error(f"Error resetting password: {e}")
        return False

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict())
    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
    except Exception as e:
        logging.error(f"Error creating product: {e}")
        db.rollback()
        return None
    return db_product

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Product).offset(skip).limit(limit).all()

def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    db_order = models.Order(**order.dict())
    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        logging.error(f"Error creating order: {e}")
        db.rollback()
        return None

def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Order).offset(skip).limit(limit).all()
