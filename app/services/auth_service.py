from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

from passlib.context import CryptContext
from pwdlib import PasswordHash
import jwt
from jwt import InvalidTokenError
from fastapi import Cookie, HTTPException
from starlette import status

from app.config import settings
from app.repositories.users_repository import get_user_by_id_public
from app.repositories.refresh_session_repository import is_refresh_session_family_active

ALGORITHM = "HS256"
SESSION_COOKIE_NAME = "session"
REFRESH_COOKIE_NAME = "refresh_session"
DEVICE_COOKIE_NAME = "device_id"

legacy_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_device_token() -> str:
    return secrets.token_urlsafe(32)


def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRES_DAYS
    )

def get_password_hash(password: str):
    return password_hasher.hash(password)


def verify_login_password(plain_password: str, stored_hash: str | None) -> bool:
    if len(plain_password) > 128:
        password_hasher.verify("invalid-password", DUMMY_PASSWORD_HASH)
        return False
    if stored_hash is None:
        password_hasher.verify(plain_password, DUMMY_PASSWORD_HASH)
        return False
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        if len(plain_password.encode("utf-8")) > 72:
            legacy_password_context.verify("invalid-password", stored_hash)
            return False
        return legacy_password_context.verify(plain_password, stored_hash)
    if stored_hash.startswith("$argon2"):
        return password_hasher.verify(plain_password, stored_hash)
    password_hasher.verify(plain_password, DUMMY_PASSWORD_HASH)
    return False


def password_hash_needs_upgrade(stored_hash: str) -> bool:
    return stored_hash.startswith(("$2a$", "$2b$", "$2y$"))

def create_access_token(data: dict):
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES
    )

    payload= data.copy()
    payload.update({
        "aud": settings.JWT_AUDIENCE,
        "exp": expires_at,
        "iat": issued_at,
        "iss": settings.JWT_ISSUER,
    })

    token = jwt.encode(payload,settings.SECRET_KEY, algorithm=ALGORITHM)

    return token

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"require": ["aud", "exp", "iat", "iss", "sub", "sid"]},
        )

        return payload

    except InvalidTokenError:
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

    payload = decode_access_token(session)
    user_id = _authenticated_session_user_id(payload)
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

    return _authenticated_session_user_id(decode_access_token(session))


def _authenticated_session_user_id(payload: dict) -> int:
    user_id = payload.get("sub")
    family_id = payload.get("sid")
    try:
        parsed_user_id = int(user_id)
        parsed_family_id = UUID(str(family_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    if not is_refresh_session_family_active(
        parsed_user_id,
        parsed_family_id,
        settings.REFRESH_TOKEN_IDLE_DAYS,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired",
        )
    return parsed_user_id
