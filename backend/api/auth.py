import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Cookie, Header, HTTPException, status
from sqlalchemy import select

from backend.database.tables import UserRow

AUTH_COOKIE_NAME = "plantops_session"
TOKEN_TTL_MINUTES = 30


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return "scrypt${}${}".format(
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_text, digest_text = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AuthService:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        if session_factory and not os.getenv("AUTH_SECRET_KEY", "").strip():
            raise RuntimeError("AUTH_SECRET_KEY must be configured when using database authentication.")

    @property
    def secret(self) -> str:
        return os.getenv("AUTH_SECRET_KEY", "").strip() or "development-only-change-this-secret"

    def bootstrap_user(self) -> None:
        if not self.session_factory:
            return
        username = os.getenv("AUTH_USERNAME", "").strip()
        password = os.getenv("AUTH_PASSWORD", "")
        if not username or not password:
            return
        with self.session_factory.begin() as session:
            user = session.scalar(select(UserRow).where(UserRow.username == username))
            if user is None:
                session.add(UserRow(username=username, password_hash=_hash_password(password), role="admin"))

    def authenticate(self, username: str, password: str) -> UserRow | None:
        if self.session_factory:
            with self.session_factory() as session:
                user = session.scalar(select(UserRow).where(UserRow.username == username))
                if user and user.is_active and _verify_password(password, user.password_hash):
                    return user
                return None
        configured_username = os.getenv("AUTH_USERNAME", "").strip()
        configured_password = os.getenv("AUTH_PASSWORD", "")
        if username == configured_username and hmac.compare_digest(password, configured_password):
            return UserRow(username=username, role="admin", is_active=True)
        return None

    def issue_token(self, user: UserRow) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.username,
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(minutes=TOKEN_TTL_MINUTES),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def decode_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self.secret, algorithms=["HS256"])


def require_authenticated_user(
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> dict[str, Any]:
    token = session_cookie
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    try:
        return jwt.decode(
            token,
            os.getenv("AUTH_SECRET_KEY", "").strip() or "development-only-change-this-secret",
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
