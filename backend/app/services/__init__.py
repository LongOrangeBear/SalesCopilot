"""Сервисы -- бизнес-логика и интеграции с внешними API."""

from app.services.stt import SpeechKitSTTClient, stt_client
from app.services.llm import LLMService, llm_service

__all__ = [
    "SpeechKitSTTClient",
    "stt_client",
    "LLMService",
    "llm_service",
]
