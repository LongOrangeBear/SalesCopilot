"""Менеджер WebSocket-соединений для дашборда."""

import json
import logging
import time

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class DashboardConnectionManager:
    """Менеджер WebSocket-соединений для дашборда."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

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


# Глобальный экземпляр
ws_manager = DashboardConnectionManager()
