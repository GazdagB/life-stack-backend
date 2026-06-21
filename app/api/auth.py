from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from starlette import status
from starlette.exceptions import HTTPException

from app.config import settings
from app.repositories.users_repository import create_user, get_user_by_username_public, get_user_by_email_public, \
    get_user_pw_hash, get_user_by_username_private
from app.services.auth_service import get_password_hash, verify_password, create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

class UserCreate(BaseModel):
    username: str = Field(min_length=3,max_length=20)
    email: EmailStr
    plain_password: str = Field(min_length=8, max_length=128)

@router.post("/register")
def register_user(user: UserCreate):
    existing_user = get_user_by_username_public(user.username)
    existing_user_email = get_user_by_email_public(user.email)

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )

    if existing_user_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    password_hash = get_password_hash(user.plain_password)
    return create_user(user.username,user.email, password_hash)

@router.post("/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username_private(form_data.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credentials incorrect",
        )

    password_is_valid = verify_password(
        form_data.password,
        user["password_hash"],
    )

    if not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credentials incorrect",
        )

    token = create_access_token(data={"sub": str(user["id"])})

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRES_MINUTES * 60,
    }

