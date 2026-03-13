"""SalesCopilot Backend -- фабрика FastAPI-приложения."""

import asyncio
import logging
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

logger = logging.getLogger(__name__)


async def _periodic_broadcast(wm, sm) -> None:
    """Периодическая отправка обновлений дашбордам (каждую 1 сек).

    Обеспечивает live-обновление таймера, current_speaker и pipeline_timings.
    """
    while True:
        await asyncio.sleep(1.0)
        try:
            if sm.active_count > 0 and wm.active_connections:
                await wm.broadcast("calls_update", {
                    "active_calls": [s.to_dict() for s in sm.active_calls],
                    "archived_calls": [s.to_dict() for s in sm.archived_calls],
                })
        except Exception as e:
            logger.error(f"Periodic broadcast: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    logger.info("SalesCopilot backend запускается...")
    logger.info(f"Yandex Folder ID: {settings.yandex_folder_id}")

    # Создаём демо-сессию для разработки
    from app.demo.fixtures import create_demo_session
    create_demo_session()
    logger.info("Демо-сессия создана")

    # Запускаем AMI-клиент для отслеживания реальных звонков
    from app.services.ami import ami_client
    await ami_client.start()

    # Запускаем AudioSocket-сервер для приёма аудио из Asterisk
    from app.services.audiosocket import audiosocket_server
    await audiosocket_server.start()

    # Запускаем периодический broadcast для live-обновлений
    from app.models.call_session import session_manager
    from app.core.ws_manager import ws_manager
    broadcast_task = asyncio.create_task(_periodic_broadcast(ws_manager, session_manager))
    logger.info("Periodic broadcast запущен")

    yield

    # Shutdown
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

    await audiosocket_server.stop()
    await ami_client.stop()

    from app.services.stt import stt_client
    from app.services.llm import llm_service
    await stt_client.close()
    await llm_service.close()
    logger.info("SalesCopilot backend остановлен.")


def create_app() -> FastAPI:
    """Фабрика приложения."""
    # Structured logging (JSON-формат)
    import sys
    log_handler = logging.StreamHandler(sys.stdout)

    try:
        from pythonjsonlogger import json as jsonlogger
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
        log_handler.setFormatter(formatter)
    except ImportError:
        # Fallback: если pythonjsonlogger не установлен
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logging.basicConfig(level=logging.INFO, handlers=[log_handler])

    application = FastAPI(
        title="SalesCopilot API",
        description="Backend для AI Sales Copilot",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS -- ограничен до dashboard
    allowed_origins = ["http://localhost:5173", "http://localhost:5174"]
    if settings.dashboard_url:
        allowed_origins.append(settings.dashboard_url)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключение роутеров
    from app.routes import health_router, calls_router, ws_router, settings_router
    application.include_router(health_router)
    application.include_router(calls_router)
    application.include_router(ws_router)
    application.include_router(settings_router)

    return application
