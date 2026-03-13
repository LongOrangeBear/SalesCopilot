"""Менеджер WebSocket-соединений для дашборда."""

import json
import logging
import time
from collections import deque

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Максимум лог-записей в буфере
MAX_LOG_ENTRIES = 200


class DashboardConnectionManager:
    """Менеджер WebSocket-соединений для дашборда."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._log_buffer: deque[dict] = deque(maxlen=MAX_LOG_ENTRIES)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dashboard WS подключён. Всего: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Dashboard WS отключён. Всего: {len(self.active_connections)}")

    async def broadcast(self, event: str, data: dict):
        """Отправляет сообщение всем подключённым дашбордам."""
        message = json.dumps({"event": event, "data": data, "timestamp": time.time()})
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    async def broadcast_log(
        self,
        source: str,
        message: str,
        details: str | None = None,
        level: str = "info",
    ) -> None:
        """Отправляет pipeline log event всем дашбордам и сохраняет в буфер.

        Args:
            source: Источник (AudioSocket, STT, AMI и т.д.)
            message: Текст сообщения
            details: Дополнительные детали (опционально)
            level: Уровень (info, warning, error)
        """
        entry = {
            "timestamp": time.time(),
            "source": source,
            "message": message,
            "details": details,
            "level": level,
        }
        self._log_buffer.append(entry)

        if self.active_connections:
            await self.broadcast("pipeline_log", entry)

    def get_recent_logs(self) -> list[dict]:
        """Возвращает последние лог-записи из буфера."""
        return list(self._log_buffer)


# Глобальный экземпляр
ws_manager = DashboardConnectionManager()
