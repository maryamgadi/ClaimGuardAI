"""Interface d'accès : API REST (FastAPI) ou CLI."""

from .server import create_app

__all__ = ["create_app"]
