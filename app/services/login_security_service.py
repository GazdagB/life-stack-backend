import hashlib
import hmac

from fastapi import HTTPException
from starlette import status

from app.config import settings
from app.repositories.auth_rate_limit_repository import (
    clear_auth_rate_limits,
    consume_auth_rate_limits,
)


def _fingerprint(scope: str, value: str) -> str:
    normalized = value.strip().casefold()
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{scope}:{normalized}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def login_rate_limit_keys(client_ip: str, username: str) -> list[tuple[str, str]]:
    return [
        ("login_ip", _fingerprint("login_ip", client_ip)),
        ("login_account", _fingerprint("login_account", username)),
    ]


def enforce_login_rate_limit(client_ip: str, username: str) -> list[tuple[str, str]]:
    keys = login_rate_limit_keys(client_ip, username)
    retry_after = consume_auth_rate_limits(
        [
            (*keys[0], settings.LOGIN_RATE_LIMIT_IP_ATTEMPTS),
            (*keys[1], settings.LOGIN_RATE_LIMIT_ACCOUNT_ATTEMPTS),
        ],
        settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    return keys


def clear_successful_login_limits(keys: list[tuple[str, str]]):
    clear_auth_rate_limits(keys)
