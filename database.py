from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = 'postgresql://postgres:2308@localhost/delivery2'

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
