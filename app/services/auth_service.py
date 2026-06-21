from datetime import datetime, timedelta, timezone

from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException
from starlette import status

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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    return get_user_id_from_token(token)

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
