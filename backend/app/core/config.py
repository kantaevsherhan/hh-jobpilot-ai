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
    def database_path(self) -> Path | None:
        """Путь к файлу базы. None, если СУБД не файловая.

        Одно место разбора URL на всё приложение: раньше путь собирали
        трижды и по-разному, из-за чего корень репозитория попадал в него
        дважды и резервное копирование падало.
        """
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if self.database_url.startswith(prefix):
                raw = self.database_url[len(prefix) :]
                if not raw or raw == ":memory:":
                    return None
                path = Path(raw)
                # Относительный путь считаем от корня репозитория, иначе база
                # создаётся там, откуда запустили uvicorn
                return path if path.is_absolute() else (ROOT_DIR / path).resolve()
        return None

    @property
    def sqlalchemy_url(self) -> str:
        path = self.database_path
        if path is None:
            return self.database_url
        return f"sqlite+aiosqlite:///{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
