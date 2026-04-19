"""Настройки из переменных окружения и .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.assets import get_project_root


class Settings(BaseSettings):
    """Параметры приложения, читаемые из .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: Path = Field(default=Path("app.log"), validation_alias="LOG_FILE")
    database_path: Path = Field(
        default=Path("encrypted.db"),
        validation_alias="DATABASE_PATH",
    )
    pbkdf2_iterations: int = Field(
        default=390_000,
        validation_alias="PBKDF2_ITERATIONS",
        ge=100_000,
        le=2_000_000,
    )

    def resolved_database_path(self) -> Path:
        """Возвращает абсолютный путь к БД относительно корня проекта/EXE."""
        p = self.database_path
        if p.is_absolute():
            return p
        return get_project_root() / p

    def resolved_log_file(self) -> Path:
        """Возвращает абсолютный путь к файлу логов."""
        p = self.log_file
        if p.is_absolute():
            return p
        return get_project_root() / p
