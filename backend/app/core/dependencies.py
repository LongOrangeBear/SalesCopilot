"""FastAPI зависимости (Dependency Injection)."""

from app.models.call_session import SessionManager, session_manager
from app.services.stt import SpeechKitSTTClient, stt_client
from app.services.llm import LLMService, llm_service
from app.core.ws_manager import DashboardConnectionManager, ws_manager


def get_session_manager() -> SessionManager:
    """DI: менеджер сессий звонков."""
    return session_manager


def get_stt_client() -> SpeechKitSTTClient:
    """DI: клиент SpeechKit STT."""
    return stt_client


def get_llm_service() -> LLMService:
    """DI: клиент OpenAI LLM."""
    return llm_service


def get_ws_manager() -> DashboardConnectionManager:
    """DI: менеджер WebSocket-соединений."""
    return ws_manager
