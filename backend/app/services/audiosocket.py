"""AudioSocket Server -- прием аудиопотока из Asterisk.

Asterisk передает аудио через AudioSocket (Asterisk 16+):
- TCP-соединение, Asterisk отправляет PCM-чанки
- Каждое соединение привязано к call_id (UUID из dialplan)
- Два канала на звонок = два TCP-соединения (клиент + менеджер)

Протокол AudioSocket:
- 3 байта header: [type(1) + length(2)]
- Type 0x10 = UUID (16 bytes) -- ID звонка
- Type 0x11 = Audio data (LINEAR16_PCM, 8kHz, mono)
- Type 0x01 = Hangup
- Type 0x02 = Error
"""

import asyncio
import logging
import struct
import time
import uuid
from typing import Dict, Optional

from config import settings

logger = logging.getLogger(__name__)

# AudioSocket frame types
FRAME_TYPE_UUID = 0x10
FRAME_TYPE_AUDIO = 0x11
FRAME_TYPE_HANGUP = 0x01
FRAME_TYPE_ERROR = 0x02

# Настройки
AUDIOSOCKET_PORT = getattr(settings, "audiosocket_port", 9092)
CHUNK_DURATION_MS = 400  # Отправлять в STT каждые ~400мс

# Логировать статистику аудио каждые N чанков
LOG_AUDIO_EVERY_N_CHUNKS = 25


class AudioSocketSession:
    """Сессия одного AudioSocket-соединения."""

    def __init__(self, call_id: str, speaker: str) -> None:
        self.call_id = call_id
        self.speaker = speaker  # "client" или "manager"
        self.audio_buffer = bytearray()
        self.started_at = time.time()
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.chunk_count: int = 0
        self.total_bytes: int = 0

    async def feed_audio(self, data: bytes) -> None:
        """Добавить аудио-данные в очередь для STT."""
        self.chunk_count += 1
        self.total_bytes += len(data)
        await self._audio_queue.put(data)

    async def audio_generator(self):
        """Async-генератор для STT streaming."""
        while True:
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=5.0)
                if chunk is None:  # Сигнал завершения
                    return
                yield chunk
            except asyncio.TimeoutError:
                logger.warning("AudioSocket %s: таймаут ожидания аудио", self.call_id)
                return

    async def stop(self) -> None:
        """Сигнал завершения."""
        await self._audio_queue.put(None)


class AudioSocketServer:
    """TCP-сервер AudioSocket для приема аудио из Asterisk."""

    def __init__(self) -> None:
        self._server: Optional[asyncio.AbstractServer] = None
        self._sessions: Dict[str, AudioSocketSession] = {}
        self._stt_tasks: Dict[str, asyncio.Task] = {}

    async def _emit_log(
        self, message: str, details: str | None = None, level: str = "info"
    ) -> None:
        """Отправить pipeline log через ws_manager."""
        try:
            from app.core.ws_manager import ws_manager
            await ws_manager.broadcast_log("AudioSocket", message, details, level)
        except Exception:
            pass  # Не ломаем pipeline из-за логирования

    async def start(self, host: str = "0.0.0.0", port: int = AUDIOSOCKET_PORT) -> None:
        """Запуск TCP-сервера."""
        self._server = await asyncio.start_server(
            self._handle_connection, host, port
        )
        logger.info("AudioSocket: cервер запущен на %s:%d", host, port)
        await self._emit_log(
            f"Сервер запущен на {host}:{port}",
            f"Ожидание AudioSocket-соединений от Asterisk",
        )

    async def stop(self) -> None:
        """Остановка сервера."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Остановить все STT-задачи
        for task in self._stt_tasks.values():
            task.cancel()

        # Остановить все сессии
        for session in self._sessions.values():
            await session.stop()

        self._sessions.clear()
        self._stt_tasks.clear()
        logger.info("AudioSocket: cервер остановлен")

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Обработка одного AudioSocket-соединения."""
        addr = writer.get_extra_info("peername")
        logger.info("AudioSocket: новое соединение от %s", addr)
        await self._emit_log(
            f"Новое соединение от {addr}",
            "Ожидание UUID звонка...",
        )

        call_id: Optional[str] = None
        session: Optional[AudioSocketSession] = None

        try:
            while True:
                # Читаем header: type (1 byte) + length (2 bytes, big-endian)
                header = await reader.readexactly(3)
                frame_type = header[0]
                frame_length = struct.unpack(">H", header[1:3])[0]

                if frame_length > 0:
                    payload = await reader.readexactly(frame_length)
                else:
                    payload = b""

                if frame_type == FRAME_TYPE_UUID:
                    # UUID звонка (16 bytes)
                    call_id = str(uuid.UUID(bytes=payload[:16]))
                    logger.info("AudioSocket: call_id = %s", call_id)

                    # Определяем speaker (первое соединение = client, второе = manager)
                    speaker = "manager" if call_id in self._sessions else "client"
                    session_key = f"{call_id}_{speaker}"

                    session = AudioSocketSession(call_id, speaker)
                    self._sessions[session_key] = session
                    logger.info("AudioSocket: сессия %s speaker=%s", call_id[:8], speaker)

                    await self._emit_log(
                        f"UUID получен: {call_id[:8]}... speaker={speaker}",
                        f"Полный UUID: {call_id} | Адрес: {addr}",
                    )

                    # Запускаем STT для этого потока
                    stt_task = asyncio.create_task(
                        self._run_stt(session)
                    )
                    self._stt_tasks[session_key] = stt_task

                elif frame_type == FRAME_TYPE_AUDIO and session:
                    # Аудио-данные
                    await session.feed_audio(payload)

                    # Периодическое логирование статистики аудио-чанков
                    if session.chunk_count % LOG_AUDIO_EVERY_N_CHUNKS == 0:
                        elapsed = time.time() - session.started_at
                        kb = session.total_bytes / 1024
                        await self._emit_log(
                            f"Аудио [{session.speaker}]: {session.chunk_count} чанков, {kb:.1f} KB",
                            f"call_id={session.call_id[:8]}... | Время: {elapsed:.0f}с | Размер чанка: {len(payload)} байт",
                        )

                elif frame_type == FRAME_TYPE_HANGUP:
                    logger.info("AudioSocket: hangup для %s", call_id)
                    elapsed = time.time() - session.started_at if session else 0
                    await self._emit_log(
                        f"Hangup: {call_id[:8] if call_id else '???'}...",
                        f"Длительность: {elapsed:.0f}с | Чанков: {session.chunk_count if session else 0}",
                        level="warning",
                    )
                    break

                elif frame_type == FRAME_TYPE_ERROR:
                    logger.error("AudioSocket: ошибка от Asterisk для %s", call_id)
                    await self._emit_log(
                        f"Ошибка от Asterisk: {call_id[:8] if call_id else '???'}",
                        f"Payload: {payload.hex()[:100]}",
                        level="error",
                    )
                    break

        except asyncio.IncompleteReadError:
            logger.info("AudioSocket: соединение закрыто для %s", call_id)
            await self._emit_log(
                f"Соединение закрыто: {call_id[:8] if call_id else '???'}",
                level="warning",
            )
        except Exception as e:
            logger.error("AudioSocket: %s для %s", e, call_id)
            await self._emit_log(
                f"Ошибка: {str(e)[:100]}",
                f"call_id={call_id}",
                level="error",
            )
        finally:
            # Cleanup
            if session:
                await session.stop()
                session_key = f"{call_id}_{session.speaker}"
                self._sessions.pop(session_key, None)
                task = self._stt_tasks.pop(session_key, None)
                if task:
                    task.cancel()

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _run_stt(self, session: AudioSocketSession) -> None:
        """Запуск STT streaming для AudioSocket-сессии."""
        from app.services.stt import stt_client
        from app.models.call_session import session_manager, Speaker

        call_session = session_manager.get_session(session.call_id)

        # Retry: AudioSocket может подключиться раньше, чем AMI создаст CallSession
        if not call_session:
            for attempt in range(5):
                await asyncio.sleep(0.5)
                call_session = session_manager.get_session(session.call_id)
                if call_session:
                    logger.info(
                        "STT: CallSession найдена после retry #%d для %s",
                        attempt + 1, session.call_id[:8],
                    )
                    break

        if not call_session:
            logger.warning(
                "STT: CallSession не найдена для %s, создаём fallback",
                session.call_id,
            )
            await self._emit_log(
                f"CallSession не найдена: {session.call_id[:8]}...",
                "Создана fallback-сессия для STT streaming",
                level="warning",
            )
            # Создаём минимальную сессию, чтобы STT мог работать
            from app.models.call_session import CallStatus
            call_session = session_manager.create_session(
                call_id=session.call_id,
                status=CallStatus.ACTIVE,
            )

        speaker = Speaker.CLIENT if session.speaker == "client" else Speaker.MANAGER

        await self._emit_log(
            f"STT streaming запущен [{session.speaker}]",
            f"call_id={session.call_id[:8]}... | Модель: general, ru-RU, 8kHz",
        )

        stt_start = time.time()

        def on_partial(text: str) -> None:
            """Промежуточный результат -- обновляем current_speaker."""
            call_session.current_speaker = session.speaker
            logger.debug("STT partial [%s]: %s", session.speaker, text[:50])

        def on_final(text: str, confidence: float) -> None:
            """Финальный результат -- добавляем в транскрипт."""
            if text.strip():
                call_session.add_utterance(
                    speaker=speaker,
                    text=text,
                    is_final=True,
                )
                # Замер STT тайминга
                stt_ms = (time.time() - stt_start) * 1000
                if call_session.pipeline_timings:
                    call_session.pipeline_timings.stt_ms = stt_ms

                logger.info(
                    "STT final [%s] (%.1f%%): %s",
                    session.speaker,
                    confidence * 100,
                    text[:80],
                )

                # Log через pipeline
                asyncio.get_event_loop().call_soon(
                    asyncio.ensure_future,
                    self._emit_log(
                        f"STT final [{session.speaker}] ({confidence*100:.0f}%): {text[:60]}",
                        f"call_id={session.call_id[:8]}... | Полный текст: {text}",
                    ),
                )

        def on_classifier(name: str, probability: float) -> None:
            """Результат классификатора."""
            if probability > 0.7:
                logger.info("STT classifier [%s]: %s = %.1f%%", session.speaker, name, probability * 100)

        def on_eou() -> None:
            """Конец фразы."""
            call_session.current_speaker = None

        try:
            await stt_client.recognize_streaming(
                audio_generator=session.audio_generator(),
                on_partial=on_partial,
                on_final=on_final,
                on_classifier=on_classifier,
                on_eou=on_eou,
            )
            elapsed = time.time() - stt_start
            await self._emit_log(
                f"STT streaming завершён [{session.speaker}]",
                f"call_id={session.call_id[:8]}... | Длительность: {elapsed:.0f}с",
            )
        except Exception as e:
            logger.error("STT streaming: %s для %s", e, session.call_id)
            await self._emit_log(
                f"STT streaming ошибка [{session.speaker}]: {str(e)[:80]}",
                f"call_id={session.call_id[:8]}... | Тип: {type(e).__name__}",
                level="error",
            )


# Синглтон
audiosocket_server = AudioSocketServer()
