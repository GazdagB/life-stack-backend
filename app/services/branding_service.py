from fastapi import HTTPException
from starlette import status

MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_SIGNATURE_BYTES = 2 * 1024 * 1024


def validate_logo(content: bytes) -> str:
    return _validate_image(content, MAX_LOGO_BYTES, "logo")


def validate_signature(content: bytes) -> str:
    return _validate_image(content, MAX_SIGNATURE_BYTES, "signature")


def _validate_image(content: bytes, max_bytes: int, label: str) -> str:
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Choose a {label} to upload",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Business {label}s must be 2 MB or smaller",
        )
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Use a PNG, JPEG, or WebP {label}",
    )
