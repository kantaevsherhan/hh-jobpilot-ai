"""Настройки приложения. Всё, что не правится из UI, живёт в .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → корень репозитория
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    database_url: str = "sqlite+aiosqlite:///./data/jobpilot.db"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b-instruct"
    ollama_num_ctx: int = 8192

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    browser_user_data_dir: str = "./data/browser/default"

    @property
    def data_dir(self) -> Path:
        return ROOT_DIR / "data"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def sqlalchemy_url(self) -> str:
        """Относительный путь к базе разворачивается от корня репозитория,
        иначе база создаётся там, откуда запустили uvicorn."""
        prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(prefix + "./"):
            relative = self.database_url[len(prefix) + 2 :]
            return f"{prefix}{ROOT_DIR / relative}"
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
