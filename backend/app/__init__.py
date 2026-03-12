"""SalesCopilot Backend -- фабрика FastAPI-приложения."""

import logging
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    logger.info("SalesCopilot backend запускается...")
    logger.info(f"Yandex Folder ID: {settings.yandex_folder_id}")

    # Создаём демо-сессию для разработки
    from app.demo.fixtures import create_demo_session
    create_demo_session()
    logger.info("Демо-сессия создана")

    yield

    # Shutdown
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
    from app.routes import health_router, calls_router, ws_router
    application.include_router(health_router)
    application.include_router(calls_router)
    application.include_router(ws_router)

    return application
