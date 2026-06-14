from fastapi import APIRouter
from app.db import get_connection
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
        return {f"Failed to connect to database: {e}"}
