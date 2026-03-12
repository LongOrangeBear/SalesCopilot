"""Yandex SpeechKit -- клиент потокового распознавания речи (streaming STT)."""

import asyncio
import logging
from typing import AsyncGenerator, Callable, Optional

import grpc
import httpx

from config import settings

logger = logging.getLogger(__name__)

# Yandex SpeechKit gRPC endpoint
STT_ENDPOINT = "stt.api.cloud.yandex.net:443"

# Параметры распознавания
SAMPLE_RATE = 8000  # Стандарт телефонии
AUDIO_ENCODING = "LINEAR16_PCM"
LANGUAGE_CODE = "ru-RU"
CHUNK_SIZE = 4096  # байтов на chunk


class SpeechKitSTTClient:
    """Потоковое распознавание речи через Yandex SpeechKit gRPC API v3.

    Использует bidirectional streaming:
    клиент отправляет аудио-чанки, сервер возвращает распознанный текст.
    """

    def __init__(self):
        self.api_key = settings.yandex_api_key
        self.folder_id = settings.yandex_folder_id
        self._channel: Optional[grpc.aio.Channel] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Получает или создаёт shared httpx-клиент."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _get_channel(self) -> grpc.aio.Channel:
        """Получает или создаёт gRPC канал."""
        if self._channel is None:
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.aio.secure_channel(STT_ENDPOINT, credentials)
        return self._channel

    async def recognize_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        on_result: Callable[[str, bool, float], None],
        language_code: str = LANGUAGE_CODE,
    ) -> None:
        """Запускает потоковое распознавание.

        Args:
            audio_generator: Асинхронный генератор аудио-чанков (LPCM 8000Hz mono).
            on_result: Callback: (текст, is_final, confidence).
            language_code: Язык распознавания.
        """
        try:
            channel = await self._get_channel()

            # В реальном проекте нужно сгенерировать stubs из Yandex Cloud API proto.
            # Пока используем REST-fallback через httpx.
            await self._recognize_rest_fallback(audio_generator, on_result, language_code)

        except Exception as e:
            logger.error(f"STT streaming error: {e}")
            raise

    async def _recognize_rest_fallback(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        on_result: Callable[[str, bool, float], None],
        language_code: str,
    ) -> None:
        """Fallback -- распознавание через REST API (не streaming,
        но работает без proto-генерации).

        Для MVP достаточно. gRPC streaming подключим, когда пойдёт реальный
        аудиопоток из Asterisk.
        """
        url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        headers = {"Authorization": f"Api-Key {self.api_key}"}
        params = {
            "lang": language_code,
            "folderId": self.folder_id,
            "format": "lpcm",
            "sampleRateHertz": str(SAMPLE_RATE),
        }

        # Собираем аудио в буфер
        audio_buffer = bytearray()
        async for chunk in audio_generator:
            audio_buffer.extend(chunk)

        if not audio_buffer:
            logger.warning("Пустой аудиобуфер, пропускаем распознавание")
            return

        client = await self._get_http_client()
        response = await client.post(
            url,
            headers=headers,
            params=params,
            content=bytes(audio_buffer),
        )

        if response.status_code == 200:
            result = response.json()
            text = result.get("result", "")
            if text:
                on_result(text, True, 1.0)
        else:
            logger.error(
                f"STT REST ошибка: {response.status_code} -- {response.text}"
            )

    async def check_connection(self) -> dict:
        """Проверяет доступность SpeechKit API.

        Returns:
            dict с ключами 'available' (bool) и 'message' (str).
        """
        try:
            url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
            headers = {"Authorization": f"Api-Key {self.api_key}"}

            client = await self._get_http_client()
            # Отправляем пустой запрос -- ожидаем 400 "audio should be not empty"
            # Это значит, что аутентификация прошла успешно
            response = await client.post(url, headers=headers, content=b"")

            if response.status_code == 400:
                body = response.json()
                if "audio should be not empty" in body.get("error_message", ""):
                    return {"available": True, "message": "SpeechKit STT: OK"}

            if response.status_code == 401 or response.status_code == 403:
                return {
                    "available": False,
                    "message": f"SpeechKit STT: ошибка авторизации ({response.status_code})",
                }

            return {
                "available": False,
                "message": f"SpeechKit STT: неожиданный статус {response.status_code}",
            }
        except Exception as e:
            return {"available": False, "message": f"SpeechKit STT: {str(e)}"}

    async def close(self):
        """Закрывает gRPC канал и HTTP-клиент."""
        if self._channel:
            await self._channel.close()
            self._channel = None
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None


# Глобальный экземпляр
stt_client = SpeechKitSTTClient()
