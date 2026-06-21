from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt

from app.config import settings

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hash_password) -> bool:
    return pwd_context.verify(plain_password,hash_password)

def create_access_token(data: dict):
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES
    )

    payload= data.copy()
    payload.update({"exp": expires_at})

    token = jwt.encode(payload,settings.SECRET_KEY, algorithm=ALGORITHM)

    return token