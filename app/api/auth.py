from datetime import datetime, timezone
import logging
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, File, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from starlette import status
from starlette.exceptions import HTTPException

from app.config import settings
from app.repositories.users_repository import (
    create_user,
    delete_user_avatar,
    get_user_avatar,
    get_user_by_email_public,
    get_user_password_hash_by_id,
    get_user_by_username_private,
    get_user_by_username_public,
    update_user_avatar,
    update_user_password_hash,
    update_user_profile,
    update_user_language,
)
from app.repositories.refresh_session_repository import (
    create_refresh_session,
    list_active_refresh_sessions,
    revoke_all_refresh_sessions,
    revoke_other_refresh_sessions,
    revoke_refresh_session,
    revoke_refresh_session_family,
    rotate_refresh_session,
)
from app.services.auth_service import (
    DEVICE_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_access_token,
    generate_device_token,
    generate_refresh_token,
    get_current_user,
    get_password_hash,
    hash_device_token,
    hash_refresh_token,
    password_hash_needs_upgrade,
    refresh_token_expires_at,
    verify_login_password,
)
from app.services.profile_service import MAX_AVATAR_BYTES, validate_avatar
from app.services.login_security_service import (
    clear_successful_login_limits,
    enforce_login_rate_limit,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

security_logger = logging.getLogger("life_stack.security")
DEVICE_COOKIE_MAX_AGE = 400 * 24 * 60 * 60


def _user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    return value[:500] if value else None


def _set_access_cookie(response: Response, user_id: int, family_id: UUID):
    max_age = settings.ACCESS_TOKEN_EXPIRES_MINUTES * 60
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_access_token(data={"sub": str(user_id), "sid": str(family_id)}),
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
        max_age=max_age,
    )
    return max_age


def _set_refresh_cookie(response: Response, token: str, expires_at: datetime):
    utc_expires_at = expires_at.astimezone(timezone.utc)
    max_age = max(0, int((utc_expires_at - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/auth",
        max_age=max_age,
        expires=utc_expires_at,
    )
    return max_age


def _device_identity(response: Response, device_id: str | None) -> tuple[str, str]:
    token = device_id if device_id and len(device_id) <= 128 else generate_device_token()
    response.set_cookie(
        key=DEVICE_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
        max_age=DEVICE_COOKIE_MAX_AGE,
    )
    return token, hash_device_token(token)


def _clear_auth_cookies(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth")


def _invalid_refresh_response():
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Session has expired"},
    )
    _clear_auth_cookies(response)
    return response

class UserCreate(BaseModel):
    username: str = Field(min_length=3,max_length=20)
    email: EmailStr
    plain_password: str = Field(min_length=15, max_length=128)


class ProfileUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: EmailStr = Field(max_length=50)
    display_name: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=280)


class PreferencesUpdate(BaseModel):
    preferred_language: Literal["en", "de", "hu"]


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=15, max_length=128)

@router.post("/register")
def register_user(user: UserCreate):
    if not settings.REGISTRATION_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
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
def login_user(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    device_id: str | None = Cookie(default=None),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_keys = enforce_login_rate_limit(client_ip, form_data.username)
    user = get_user_by_username_private(form_data.username)
    password_is_valid = verify_login_password(
        form_data.password,
        user["password_hash"] if user else None,
    )

    if not password_is_valid:
        security_logger.warning(
            "login_failed user_id=%s ip=%s",
            user["id"] if user else "unknown",
            client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credentials incorrect",
        )

    if password_hash_needs_upgrade(user["password_hash"]):
        update_user_password_hash(user["id"], get_password_hash(form_data.password))
    clear_successful_login_limits(rate_limit_keys)
    security_logger.info("login_succeeded user_id=%s ip=%s", user["id"], client_ip)

    refresh_token = generate_refresh_token()
    refresh_expires_at = refresh_token_expires_at()
    family_id = uuid4()
    _, device_hash = _device_identity(response, device_id)
    create_refresh_session(
        user["id"],
        family_id,
        hash_refresh_token(refresh_token),
        refresh_expires_at,
        _user_agent(request),
        device_hash,
    )
    access_max_age = _set_access_cookie(response, user["id"], family_id)
    refresh_max_age = _set_refresh_cookie(response, refresh_token, refresh_expires_at)

    return {
        "user": {key: value for key, value in user.items() if key != "password_hash"},
        "expires_in": access_max_age,
        "refresh_expires_in": refresh_max_age,
    }


@router.post("/refresh")
def refresh_user_session(
    request: Request,
    response: Response,
    refresh_session: str | None = Cookie(default=None),
    device_id: str | None = Cookie(default=None),
):
    if refresh_session is None:
        return _invalid_refresh_response()

    next_refresh_token = generate_refresh_token()
    device_token = device_id if device_id and len(device_id) <= 128 else generate_device_token()
    rotated = rotate_refresh_session(
        hash_refresh_token(refresh_session),
        hash_refresh_token(next_refresh_token),
        settings.REFRESH_TOKEN_IDLE_DAYS,
        _user_agent(request),
        hash_device_token(device_token),
    )
    if rotated is None:
        return _invalid_refresh_response()

    _device_identity(response, device_token)

    access_max_age = _set_access_cookie(
        response,
        rotated["user_id"],
        rotated["family_id"],
    )
    refresh_max_age = _set_refresh_cookie(
        response,
        next_refresh_token,
        rotated["expires_at"],
    )
    return {
        "expires_in": access_max_age,
        "refresh_expires_in": refresh_max_age,
    }


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/profile")
def update_profile(
    profile: ProfileUpdate,
    current_user=Depends(get_current_user),
):
    username = profile.username.strip()
    display_name = profile.display_name.strip() if profile.display_name else None
    bio = profile.bio.strip() if profile.bio else None

    if len(username) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Username must contain at least 3 characters",
        )

    return update_user_profile(
        current_user["id"],
        username,
        str(profile.email).lower(),
        display_name or None,
        bio or None,
    )


@router.put("/settings")
def update_preferences(
    preferences: PreferencesUpdate,
    current_user=Depends(get_current_user),
):
    return update_user_language(
        current_user["id"],
        preferences.preferred_language,
    )


@router.get("/sessions")
def get_active_sessions(
    current_user=Depends(get_current_user),
    refresh_session: str | None = Cookie(default=None),
):
    current_token_hash = hash_refresh_token(refresh_session) if refresh_session else None
    return list_active_refresh_sessions(
        current_user["id"],
        current_token_hash,
        settings.REFRESH_TOKEN_IDLE_DAYS,
    )


@router.delete("/sessions/{family_id}")
def revoke_device_session(
    family_id: UUID,
    response: Response,
    current_user=Depends(get_current_user),
    refresh_session: str | None = Cookie(default=None),
):
    current_token_hash = hash_refresh_token(refresh_session) if refresh_session else None
    active_sessions = list_active_refresh_sessions(
        current_user["id"],
        current_token_hash,
        settings.REFRESH_TOKEN_IDLE_DAYS,
    )
    target = next((item for item in active_sessions if item["family_id"] == family_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    revoke_refresh_session_family(current_user["id"], family_id)
    if target["is_current"]:
        _clear_auth_cookies(response)
    security_logger.info(
        "session_revoked user_id=%s family_id=%s current=%s",
        current_user["id"],
        family_id,
        target["is_current"],
    )
    return {"message": "Session revoked", "current_session_revoked": target["is_current"]}


@router.post("/sessions/revoke-others")
def revoke_other_device_sessions(
    current_user=Depends(get_current_user),
    refresh_session: str | None = Cookie(default=None),
):
    if refresh_session is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Current device session is unavailable. Sign in again.",
        )
    revoked_count = revoke_other_refresh_sessions(
        current_user["id"],
        hash_refresh_token(refresh_session),
    )
    if revoked_count is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Current device session is unavailable. Sign in again.",
        )
    security_logger.info(
        "other_sessions_revoked user_id=%s count=%s",
        current_user["id"],
        revoked_count,
    )
    return {"message": "Other sessions revoked", "revoked_count": revoked_count}


@router.post("/change-password")
def change_password(
    passwords: PasswordChange,
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
    refresh_session: str | None = Cookie(default=None),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_keys = enforce_login_rate_limit(client_ip, current_user["username"])
    stored_hash = get_user_password_hash_by_id(current_user["id"])
    if not verify_login_password(passwords.current_password, stored_hash):
        security_logger.warning(
            "password_change_failed user_id=%s ip=%s",
            current_user["id"],
            client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    clear_successful_login_limits(rate_limit_keys)
    if verify_login_password(passwords.new_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    update_user_password_hash(current_user["id"], get_password_hash(passwords.new_password))
    revoked_count = None
    if refresh_session is not None:
        revoked_count = revoke_other_refresh_sessions(
            current_user["id"],
            hash_refresh_token(refresh_session),
        )
    if revoked_count is None:
        revoked_count = revoke_all_refresh_sessions(current_user["id"])
        _clear_auth_cookies(response)

    security_logger.info(
        "password_changed user_id=%s revoked_sessions=%s",
        current_user["id"],
        revoked_count,
    )
    return {"message": "Password changed", "revoked_sessions": revoked_count}


@router.post("/profile/avatar")
async def upload_profile_avatar(
    avatar: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    content = await avatar.read(MAX_AVATAR_BYTES + 1)
    content_type = validate_avatar(content)
    return update_user_avatar(current_user["id"], content, content_type)


@router.get("/profile/avatar")
def read_profile_avatar(current_user=Depends(get_current_user)):
    avatar = get_user_avatar(current_user["id"])
    if avatar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile picture not found",
        )
    return Response(
        content=avatar["avatar_data"],
        media_type=avatar["avatar_content_type"],
        headers={"Cache-Control": "private, no-cache"},
    )


@router.delete("/profile/avatar")
def remove_profile_avatar(current_user=Depends(get_current_user)):
    return delete_user_avatar(current_user["id"])


@router.post("/logout")
def logout_user(
    response: Response,
    refresh_session: str | None = Cookie(default=None),
):
    if refresh_session is not None:
        revoke_refresh_session(hash_refresh_token(refresh_session))
    _clear_auth_cookies(response)

    return {"message": "Logged out"}
