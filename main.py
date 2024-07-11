from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
import crud, models, schemas, utils
from database import SessionLocal, engine
from dependencies import get_db, get_current_user, add_token_to_blacklist
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware
import logging
from sqlalchemy.orm import joinedload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/signup/", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info("Signup attempt for user: %s", user.username)
    try:
        db_user = crud.get_user_by_username(db, username=user.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        db_user = crud.get_user_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        created_user = crud.create_user(db=db, user=user)
        if created_user is None:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        logger.info(f"User created successfully: {created_user.username}")
        return created_user
    except Exception as e:
        db.rollback()
        logger.error(f"IntegrityError: {e}")
        raise HTTPException(status_code=400, detail="Username or Email already exists")
    
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    logger.info("Login attempt for user: %s", login_data.username)
    user = crud.authenticate_user(db, username=login_data.username, password=login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/password-reset-request/")
def password_reset_request(password_reset_request: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    logger.info("Password reset request for email: %s", password_reset_request.email)
    user = crud.get_user_by_email(db, email=password_reset_request.email)
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")
    reset_token = crud.create_reset_token(user)
    return {"reset_token": reset_token}

@app.post("/password-reset-confirm/")
def password_reset_confirm(password_reset_confirm: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    logger.info("Password reset confirm attempt")
    success = crud.reset_password(db, token=password_reset_confirm.reset_token, new_password=password_reset_confirm.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid token or token expired")
    return {"msg": "Password reset successful"}

@app.get("/users/profile/", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    logger.info("Fetching current user data")
    return current_user

@app.post("/logout/")
def logout(current_user: schemas.User = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    add_token_to_blacklist(token)
    logger.info("Logout attempt for user: %s", current_user.username)
    return {"msg": "Logout successful"}

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Not authorized to create products")
    logger.info("Creating product: %s", product.name)
    try:
        created_product = crud.create_product(db=db, product=product)
        db.commit()
        return created_product
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Product creation failed")

@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    logger.info("Reading products")
    products = crud.get_products(db, skip=skip, limit=limit)
    return products

@app.get("/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    logger.info("Reading product with ID: %d", product_id)
    product = crud.get_product(db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.delete("/products/{product_id}", response_model=schemas.Product)
def delete_product(product_id: int, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Not authorized to delete products")
    
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        db.query(models.Order).filter(models.Order.product_id == product_id).delete()
        db.delete(product)
        db.commit()
        return product
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Product deletion failed: {str(e)}")

@app.post("/orders/", response_model=schemas.Order)
def create_order(order: schemas.OrderCreate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Creating order for user_id: {order.user_id}")
    try:
        product = crud.get_product(db, order.product_id)
        if not product:
            raise HTTPException(status_code=400, detail="Product not found")

        created_order = crud.create_order(db=db, order=order)
        if not created_order:
            raise HTTPException(status_code=500, detail="Order creation failed")

        db.commit()
        db.refresh(created_order)
        logger.info(f"Order created successfully: {created_order}")
        return created_order
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Order creation failed")

@app.get("/orders/", response_model=List[schemas.Order])
def read_orders(skip: int = 0, limit: int = 10, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("Reading orders for user: %s", current_user.username)
    if current_user.is_staff:
        orders = crud.get_orders(db, skip=skip, limit=limit)
    else:
        orders = db.query(models.Order).filter(models.Order.user_id == current_user.id).offset(skip).limit(limit).all()
    return orders


@app.get("/orders/{order_id}", response_model=schemas.Order)
def read_order(order_id: int, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("Reading order with ID: %d", order_id)
    order = crud.get_order(db, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if not current_user.is_staff and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    return order


@app.delete("/orders/{order_id}", response_model=schemas.Order)
def delete_order(order_id: int, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        order = db.query(models.Order).options(joinedload(models.Order.product)).filter(models.Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if not current_user.is_staff and order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this order")
        
        db.delete(order)
        db.commit()
        return order
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Order deletion failed")
    except Exception as e:
        logger.error(f"Error deleting order: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Order Not Found")