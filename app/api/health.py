from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database.db import get_connection


router = APIRouter(tags=["health"])


@router.get("/healthz", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}


@router.get("/readyz", include_in_schema=False)
def readiness_check():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    return {"status": "ready"}
