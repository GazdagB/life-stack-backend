from dotenv import load_dotenv
from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("DATABASE CONNECTED:", result.scalar())
except Exception as e:
    print("DATABASE ERROR:", e)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()