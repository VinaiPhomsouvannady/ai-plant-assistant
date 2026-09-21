"""Compatibility entrypoint for `uvicorn app:app --reload`."""

from backend.app import app

__all__ = ["app"]
