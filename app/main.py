from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.expenses import router as expenses_router
from app.api.test_db import router as test_db_router
from app.api.todos import router as todos_router
from app.api.auth import router as auth_router
from app.api.recurring_expenses import router as recurring_expenses_router
from app.api.movies import router as movies_router
from app.api.invoicing import router as invoicing_router
from app.api.banking import router as banking_router
from app.api.health import router as health_router
from app.database.db import close_connection_pool, open_connection_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    open_connection_pool()
    yield
    close_connection_pool()

app = FastAPI(
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_API_DOCS else None,
    lifespan=lifespan,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
    www_redirect=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


@app.middleware("http")
async def security_policy(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site")
        if (origin and origin not in settings.ALLOWED_ORIGINS) or (
            not origin and fetch_site == "cross-site"
        ):
            return JSONResponse(status_code=403, content={"detail": "Cross-site request blocked"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Vary"] = "Origin, Sec-Fetch-Site"
    if request.url.path.startswith("/auth"):
        response.headers["Cache-Control"] = "no-store"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response

app.include_router(expenses_router)
if settings.ENABLE_DB_HEALTH_ROUTE:
    app.include_router(test_db_router)
app.include_router(todos_router)

app.include_router(auth_router)
app.include_router(recurring_expenses_router)
app.include_router(movies_router)
app.include_router(invoicing_router)
app.include_router(banking_router)
app.include_router(health_router)

@app.get("/")
async def root():
    return {"message": "LifeStack OS API is running!"}
