from fastapi import APIRouter
from pydantic import BaseModel, Field
from pydantic.v1 import EmailStr
from starlette import status
from starlette.exceptions import HTTPException

from app.repositories.users_repository import create_user, get_user_by_username_public, get_user_by_email_public
from app.services.auth_service import get_password_hash

router = APIRouter(
    prefix="auth",
    tags=["auth"]
)

class UserCreate(BaseModel):
    username: str = Field(min_length=3,max_length=20)
    email: EmailStr
    plain_password: str = Field(min_length=8, max_length=128)

@router.get("/register")
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