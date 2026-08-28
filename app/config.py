from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    REFRESH_TOKEN_IDLE_DAYS = int(os.getenv("REFRESH_TOKEN_IDLE_DAYS", "7"))
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    OMDB_API_KEY = os.getenv("OMDB_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MOVIE_MODEL = os.getenv("OPENAI_MOVIE_MODEL", "gpt-5.6-luna")
settings = Settings()
