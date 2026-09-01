from dotenv import load_dotenv
import os

load_dotenv()


def _csv_setting(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]

class Settings:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "life-stack-api")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "life-stack-web")
    ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    REFRESH_TOKEN_IDLE_DAYS = int(os.getenv("REFRESH_TOKEN_IDLE_DAYS", "7"))
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "false").lower() == "true"
    ALLOWED_ORIGINS = _csv_setting(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    ALLOWED_HOSTS = _csv_setting("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
    ENABLE_API_DOCS = os.getenv(
        "ENABLE_API_DOCS",
        "true" if ENVIRONMENT != "production" else "false",
    ).lower() == "true"
    ENABLE_DB_HEALTH_ROUTE = os.getenv("ENABLE_DB_HEALTH_ROUTE", "false").lower() == "true"
    PUBLIC_API_PREFIX = os.getenv("PUBLIC_API_PREFIX", "/api").rstrip("/")
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
    LOGIN_RATE_LIMIT_ACCOUNT_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_ACCOUNT_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_IP_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_IP_ATTEMPTS", "25"))
    OMDB_API_KEY = os.getenv("OMDB_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MOVIE_MODEL = os.getenv("OPENAI_MOVIE_MODEL", "gpt-5.6-luna")
    ENABLE_BANKING_APP_ID = os.getenv("ENABLE_BANKING_APP_ID")
    BANK_DATA_ENCRYPTION_KEY = os.getenv("BANK_DATA_ENCRYPTION_KEY")
    ENABLE_BANKING_PRIVATE_KEY = os.getenv("ENABLE_BANKING_PRIVATE_KEY")
    ENABLE_BANKING_PRIVATE_KEY_PATH = os.getenv("ENABLE_BANKING_PRIVATE_KEY_PATH")
    ENABLE_BANKING_BASE_URL = os.getenv("ENABLE_BANKING_BASE_URL", "https://api.enablebanking.com")
    ENABLE_BANKING_REDIRECT_URL = os.getenv("ENABLE_BANKING_REDIRECT_URL", "http://localhost:5173/expenses/bank-accounts/callback")
    ENABLE_BANKING_CONSENT_DAYS = min(int(os.getenv("ENABLE_BANKING_CONSENT_DAYS", "89")), 90)

    def validate(self):
        if self.PUBLIC_API_PREFIX and not self.PUBLIC_API_PREFIX.startswith("/"):
            raise RuntimeError("PUBLIC_API_PREFIX must be empty or start with /")
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "dev-secret-change-me" or len(self.SECRET_KEY) < 32:
                raise RuntimeError("JWT_SECRET_KEY must be a random value of at least 32 characters in production")
            if not self.SESSION_COOKIE_SECURE:
                raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")
            if any(origin.startswith("http://") for origin in self.ALLOWED_ORIGINS):
                raise RuntimeError("Production ALLOWED_ORIGINS must use HTTPS")
            if not self.ALLOWED_HOSTS or "*" in self.ALLOWED_HOSTS:
                raise RuntimeError("Production ALLOWED_HOSTS must explicitly list the public hostname")
            if self.ENABLE_BANKING_APP_ID and not self.ENABLE_BANKING_REDIRECT_URL.startswith("https://"):
                raise RuntimeError("Production ENABLE_BANKING_REDIRECT_URL must use HTTPS")
            if self.ENABLE_BANKING_APP_ID and not self.BANK_DATA_ENCRYPTION_KEY:
                raise RuntimeError("BANK_DATA_ENCRYPTION_KEY is required when bank synchronization is enabled")

settings = Settings()
settings.validate()
