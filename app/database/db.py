import dotenv
from psycopg_pool import ConnectionPool

from app.config import settings

dotenv.load_dotenv()
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

connection_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=settings.DB_POOL_MIN_SIZE,
    max_size=settings.DB_POOL_MAX_SIZE,
    timeout=settings.DB_POOL_TIMEOUT_SECONDS,
    kwargs={"connect_timeout": 5},
    check=ConnectionPool.check_connection,
    open=False,
    name="life-stack",
)


def open_connection_pool():
    if connection_pool.closed:
        connection_pool.open(wait=False)


def get_connection():
    open_connection_pool()
    return connection_pool.connection(timeout=settings.DB_POOL_TIMEOUT_SECONDS)


def close_connection_pool():
    connection_pool.close()
