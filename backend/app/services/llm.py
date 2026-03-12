"""Сервис проверки OpenAI LLM API."""

import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Клиент для работы с OpenAI LLM API."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Получает или создаёт httpx-клиент."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def check_connection(self) -> dict:
        """Проверяет доступность OpenAI API.

        Returns:
            dict с ключами 'available' (bool) и 'message' (str).
        """
        try:
            client = await self._get_client()
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            if resp.status_code == 200:
                return {"available": True, "message": "OpenAI: OK"}
            else:
                return {
                    "available": False,
                    "message": f"OpenAI: ошибка {resp.status_code}",
                }
        except Exception as e:
            return {"available": False, "message": f"OpenAI: {str(e)}"}

    def get_api_key_suffix(self) -> str:
        """Возвращает маскированный суффикс ключа."""
        return f"...{self.api_key[-8:]}"

    async def close(self):
        """Закрывает httpx-клиент."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Глобальный экземпляр
llm_service = LLMService()
