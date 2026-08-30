from fastapi import APIRouter, HTTPException
from app.database.db import get_connection
import psycopg

router = APIRouter(
    prefix="/db",
    tags=["db"],
)

@router.get("/ping")
def ping():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return {"message": "Connection alive"}
    except psycopg.Error as e:
        raise HTTPException(status_code=503, detail="Database unavailable") from e
