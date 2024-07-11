from sqlalchemy.orm import Session
import models, schemas, crud
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

def init_db():
    db: Session = SessionLocal()

    initial_user = crud.get_user_by_username(db, username="admin")
    if not initial_user:
        admin_user = schemas.UserCreate(
            username="admin",
            email="admin@example.com",
            password="admin123"
        )
        crud.create_user(db, user=admin_user)
        print("Created initial admin user with username 'admin' and password 'admin123'")
    db.close()

if __name__ == "__main__":
    init_db()
