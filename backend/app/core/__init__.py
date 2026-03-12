"""Core -- менеджеры, зависимости, общая инфраструктура."""

from app.core.ws_manager import DashboardConnectionManager, ws_manager
from app.core.dependencies import (
    get_session_manager,
    get_stt_client,
    get_ws_manager,
)

__all__ = [
    "DashboardConnectionManager",
    "ws_manager",
    "get_session_manager",
    "get_stt_client",
    "get_ws_manager",
]
