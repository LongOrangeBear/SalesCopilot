"""Роутеры API."""

from app.routes.health import router as health_router
from app.routes.calls import router as calls_router
from app.routes.ws import router as ws_router
from app.routes.settings import router as settings_router

__all__ = ["health_router", "calls_router", "ws_router", "settings_router"]
