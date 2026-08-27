from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Cookie, HTTPException
from starlette import status

from app.config import settings
from app.repositories.users_repository import get_user_by_id_public

ALGORITHM = "HS256"
SESSION_COOKIE_NAME = "session"
REFRESH_COOKIE_NAME = "refresh_session"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRES_DAYS
    )

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

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_user_id_from_token(token: str) -> int:
    payload = decode_access_token(token)

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    try:
        return int(user_id)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_current_user(session: str | None = Cookie(default=None)):
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = get_user_id_from_token(session)
    user = get_user_by_id_public(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    return user


def get_current_user_id(session: str | None = Cookie(default=None)) -> int:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return get_user_id_from_token(session)
