from dotenv import load_dotenv
from email_validator import EmailNotValidError, validate_email
import os

load_dotenv()


def _csv_setting(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


def _canonical_email(value: str) -> str:
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.casefold()
    except EmailNotValidError as error:
        raise RuntimeError("Email allowlist contains an invalid address") from error


def _email_allowlist_setting(name: str) -> tuple[str, ...]:
    values = [_canonical_email(value) for value in os.getenv(name, "").split(",") if value.strip()]
    if len(values) != len(set(values)):
        raise RuntimeError(f"{name} contains duplicate addresses")
    return tuple(values)


def _bounded_int_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


class Settings:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    DATABASE_URL = os.getenv("DATABASE_URL")
    DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "5"))
    DB_POOL_TIMEOUT_SECONDS = float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "5"))
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "life-stack-api")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "life-stack-web")
    ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    REFRESH_TOKEN_IDLE_DAYS = int(os.getenv("REFRESH_TOKEN_IDLE_DAYS", "7"))
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "false").lower() == "true"
    ALLOWED_USER_EMAILS = _email_allowlist_setting("ALLOWED_USER_EMAILS")
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
    OPENAI_TODO_MODEL = os.getenv("OPENAI_TODO_MODEL", OPENAI_MOVIE_MODEL)
    ENABLE_BANKING_APP_ID = os.getenv("ENABLE_BANKING_APP_ID")
    BANK_DATA_ENCRYPTION_KEY = os.getenv("BANK_DATA_ENCRYPTION_KEY")
    ENABLE_BANKING_PRIVATE_KEY = os.getenv("ENABLE_BANKING_PRIVATE_KEY")
    ENABLE_BANKING_PRIVATE_KEY_PATH = os.getenv("ENABLE_BANKING_PRIVATE_KEY_PATH")
    ENABLE_BANKING_BASE_URL = os.getenv("ENABLE_BANKING_BASE_URL", "https://api.enablebanking.com")
    ENABLE_BANKING_REDIRECT_URL = os.getenv("ENABLE_BANKING_REDIRECT_URL", "http://localhost:5173/expenses/bank-accounts/callback")
    ENABLE_BANKING_CONSENT_DAYS = _bounded_int_setting("ENABLE_BANKING_CONSENT_DAYS", 89, 1, 90)
    BANK_INITIAL_SYNC_DAYS = _bounded_int_setting("BANK_INITIAL_SYNC_DAYS", 31, 1, 365)
    BANK_SYNC_OVERLAP_DAYS = _bounded_int_setting("BANK_SYNC_OVERLAP_DAYS", 3, 0, 14)

    def is_email_allowed(self, email: str) -> bool:
        if not self.ALLOWED_USER_EMAILS:
            return self.ENVIRONMENT != "production"
        try:
            return _canonical_email(email) in self.ALLOWED_USER_EMAILS
        except RuntimeError:
            return False

    def is_owner_email(self, email: str) -> bool:
        return (
            bool(self.ALLOWED_USER_EMAILS)
            and self.is_email_allowed(email)
            and _canonical_email(email) == self.ALLOWED_USER_EMAILS[0]
        )

    def banking_configuration_error(self) -> str | None:
        if not self.ENABLE_BANKING_APP_ID:
            return "ENABLE_BANKING_APP_ID is not configured"
        if not (self.ENABLE_BANKING_PRIVATE_KEY or self.ENABLE_BANKING_PRIVATE_KEY_PATH):
            return "an Enable Banking private key is not configured"
        if not self.BANK_DATA_ENCRYPTION_KEY:
            return "BANK_DATA_ENCRYPTION_KEY is not configured"
        if self.ENVIRONMENT == "production" and not self.ENABLE_BANKING_REDIRECT_URL.startswith("https://"):
            return "the production Enable Banking redirect URL must use HTTPS"
        return None

    def validate(self):
        if self.DB_POOL_MIN_SIZE < 0:
            raise RuntimeError("DB_POOL_MIN_SIZE must be zero or greater")
        if self.DB_POOL_MAX_SIZE < max(1, self.DB_POOL_MIN_SIZE):
            raise RuntimeError("DB_POOL_MAX_SIZE must be at least one and not smaller than DB_POOL_MIN_SIZE")
        if self.DB_POOL_TIMEOUT_SECONDS <= 0:
            raise RuntimeError("DB_POOL_TIMEOUT_SECONDS must be greater than zero")
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
            if not self.ALLOWED_USER_EMAILS:
                raise RuntimeError("ALLOWED_USER_EMAILS must contain at least one address in production")
            # Banking is an optional integration. Its configuration is checked by
            # the banking client so a missing provider secret cannot take down the
            # rest of the application during startup.

settings = Settings()
settings.validate()
