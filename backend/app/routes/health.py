"""Роуты здоровья и системных метрик."""

import os

from fastapi import APIRouter, Depends

from config import settings
from app.core.dependencies import (
    get_session_manager, get_ws_manager, get_stt_client,
    get_llm_service, get_ami_client,
)
from app.core.ws_manager import DashboardConnectionManager
from app.models.call_session import SessionManager
from app.services.stt import SpeechKitSTTClient
from app.services.llm import LLMService
from app.services.ami import AsteriskAMIClient

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(
    sm: SessionManager = Depends(get_session_manager),
    wm: DashboardConnectionManager = Depends(get_ws_manager),
    stt: SpeechKitSTTClient = Depends(get_stt_client),
    llm: LLMService = Depends(get_llm_service),
    ami: AsteriskAMIClient = Depends(get_ami_client),
):
    """Статус всех сервисов."""
    stt_status = await stt.check_connection()
    llm_status = await llm.check_connection()

    return {
        "status": "ok",
        "services": {
            "stt": stt_status,
            "llm": llm_status,
            "asterisk": {
                "available": ami.is_connected,
                "message": "AMI подключён" if ami.is_connected else "AMI не подключён",
            },
            "crm": {
                "available": False,
                "message": "CRM: Bitrix24 не настроен",
            },
        },
        "active_calls": sm.active_count,
        "dashboard_connections": len(wm.active_connections),
    }


@router.get("/check-keys")
async def check_keys(
    stt: SpeechKitSTTClient = Depends(get_stt_client),
    llm: LLMService = Depends(get_llm_service),
):
    """Проверка валидности всех API-ключей."""
    stt_ok = await stt.check_connection()
    llm_status = await llm.check_connection()

    return {
        "yandex_stt": {
            "available": stt_ok,
            "message": "SpeechKit: OK" if stt_ok else "SpeechKit: недоступен",
            "api_key_suffix": f"...{settings.yandex_api_key[-8:]}",
            "folder_id": settings.yandex_folder_id,
        },
        "openai": {
            **llm_status,
            "api_key_suffix": llm.get_api_key_suffix(),
        },
    }


@router.get("/system")
async def system_info(
    sm: SessionManager = Depends(get_session_manager),
    wm: DashboardConnectionManager = Depends(get_ws_manager),
):
    """Системные метрики."""
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        load1 = load5 = load15 = 0.0

    # Информация о памяти
    mem_info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith(("MemTotal", "MemAvailable", "MemFree")):
                    parts = line.split()
                    mem_info[parts[0].rstrip(":")] = int(parts[1]) * 1024
    except Exception:
        pass

    return {
        "load_avg": {"1m": load1, "5m": load5, "15m": load15},
        "memory": mem_info,
        "active_calls": sm.active_count,
        "ws_connections": len(wm.active_connections),
        "asterisk_host": settings.asterisk_host,
    }
