"""Uvicorn entry point: ``uvicorn main:app --reload``."""

from app.main import app, create_app
from app.services.websocket import connected_devices

__all__ = ["app", "create_app", "connected_devices"]

