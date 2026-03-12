"""Роуты настроек -- текущая конфигурация системы (read-only)."""

from fastapi import APIRouter, Depends

from config import settings
from app.core.dependencies import get_stt_client, get_llm_service
from app.services.stt import SpeechKitSTTClient
from app.services.llm import LLMService

router = APIRouter(prefix="/api", tags=["settings"])


def _mask_key(key: str, visible: int = 8) -> str:
    """Маскирует API-ключ, оставляя последние N символов."""
    if len(key) <= visible:
        return "***"
    return f"...{key[-visible:]}"


@router.get("/settings")
async def get_settings(
    stt: SpeechKitSTTClient = Depends(get_stt_client),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    """Текущая конфигурация системы с замаскированными секретами."""
    stt_status = await stt.check_connection()
    llm_status = await llm.check_connection()

    return {
        "asterisk": {
            "host": settings.asterisk_host,
            "sip_port": 5060,
            "ari_port": settings.asterisk_ari_port,
            "accounts": [
                {
                    "name": "Manager",
                    "extension": 100,
                    "username": "manager",
                },
                {
                    "name": "Client",
                    "extension": 200,
                    "username": "client",
                },
            ],
            "dialplan": {
                "pattern": "_X. (universal)",
                "echo_test": 600,
                "note": "Новый аккаунт = только pjsip.conf, dialplan менять не нужно",
            },
        },
        "yandex_speechkit": {
            "folder_id": settings.yandex_folder_id,
            "api_key": _mask_key(settings.yandex_api_key),
            "status": stt_status,
        },
        "openai": {
            "api_key": _mask_key(settings.openai_api_key),
            "status": llm_status,
        },
        "server": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
            "dashboard_url": settings.dashboard_url,
        },
    }
