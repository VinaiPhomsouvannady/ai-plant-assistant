import os

from fastapi import Header, HTTPException, status


def require_write_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_ACCESS_TOKEN")
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid API access token is required for this operation.",
            headers={"WWW-Authenticate": "Bearer"},
        )
