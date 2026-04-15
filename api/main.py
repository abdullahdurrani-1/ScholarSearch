"""Compatibility entrypoint for uvicorn api.main:app."""

from api.app import app

__all__ = ["app"]
