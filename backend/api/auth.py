import os

from fastapi import Header, HTTPException, status


def require_write_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_ACCESS_TOKEN", "").strip()
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid API access token is required for this operation.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_credentials(username: str | None, password: str | None) -> bool:
    configured_username = os.getenv("AUTH_USERNAME", "").strip()
    configured_password = os.getenv("AUTH_PASSWORD", "").strip()
    if not configured_username or not configured_password:
        return False
    return username == configured_username and password == configured_password


def get_api_token() -> str:
    return os.getenv("API_ACCESS_TOKEN", "").strip()
