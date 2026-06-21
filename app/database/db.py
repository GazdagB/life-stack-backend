import psycopg
import dotenv
from app.config import settings

dotenv.load_dotenv()
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    print("DATABASE_URL not defined")
    raise ValueError("DATABASE_URL is not set")


def get_connection():
    try:
        return psycopg.connect(DATABASE_URL)
    except psycopg.OperationalError as error:
        raise RuntimeError(f"Databse connection error: {error}")
        