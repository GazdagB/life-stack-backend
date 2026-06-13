from fastapi import Depends, APIRouter
from app.database.db import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text


router = APIRouter(
    prefix="/database",
    tags=["database"],
)

@router.get("/test")
def db_test(db: Session = Depends(get_db)):
    db.execute(
        text("SELECT 1")
    )
    return {"database": "connected"}




