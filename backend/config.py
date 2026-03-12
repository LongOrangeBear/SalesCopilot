"""Конфигурация приложения -- загрузка из .env"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения из .env файла."""

    # Yandex Cloud
    yandex_api_key: str = Field(..., description="Yandex Cloud API key for SpeechKit")
    yandex_folder_id: str = Field(..., description="Yandex Cloud folder ID")

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Asterisk
    asterisk_host: str = Field(default="5.45.112.38", description="Asterisk server IP")
    asterisk_ari_port: int = Field(default=8088, description="Asterisk ARI port")
    asterisk_ari_user: str = Field(default="admin", description="Asterisk ARI username")
    asterisk_ari_password: str = Field(default="", description="Asterisk ARI password")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=True)

    # Dashboard
    dashboard_url: Optional[str] = Field(default="http://localhost:5173")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
