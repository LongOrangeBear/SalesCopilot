"""WebSocket роут для дашборда."""

import json
import logging
import time
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.core.dependencies import get_session_manager, get_ws_manager
from app.core.ws_manager import DashboardConnectionManager
from app.models.call_session import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/dashboard")
async def dashboard_ws(
    websocket: WebSocket,
    wm: DashboardConnectionManager = Depends(get_ws_manager),
    sm: SessionManager = Depends(get_session_manager),
):
    """WebSocket для real-time обновлений дашборда."""

    await wm.connect(websocket)
    try:
        # Отправляем начальное состояние
        await websocket.send_text(
            json.dumps({
                "event": "init",
                "data": {
                    "active_calls": [s.to_dict() for s in sm.active_calls],
                    "archived_calls": [s.to_dict() for s in sm.archived_calls],
                },
                "timestamp": time.time(),
            })
        )

        # Слушаем команды от дашборда
        while True:
            data = await websocket.receive_text()

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Dashboard WS: невалидный JSON от клиента")
                continue

            action = msg.get("action")

            if action == "get_calls":
                await websocket.send_text(
                    json.dumps({
                        "event": "calls_update",
                        "data": {
                            "active_calls": [s.to_dict() for s in sm.active_calls],
                            "archived_calls": [s.to_dict() for s in sm.archived_calls],
                        },
                        "timestamp": time.time(),
                    })
                )
            elif action == "get_call_detail":
                call_id = msg.get("call_id")
                session = sm.get_session(call_id)
                if session:
                    await websocket.send_text(
                        json.dumps({
                            "event": "call_detail",
                            "data": session.to_dict(),
                            "timestamp": time.time(),
                        })
                    )
            else:
                logger.debug(f"Dashboard WS: неизвестный action '{action}'")

    except WebSocketDisconnect:
        wm.disconnect(websocket)
    except Exception as e:
        logger.error(
            f"Dashboard WS ошибка: {e}\n{traceback.format_exc()}"
        )
        wm.disconnect(websocket)
