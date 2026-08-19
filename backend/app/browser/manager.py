"""Запуск Chromium и состояние сессии HH (§9).

Браузер один на всё приложение: два видимых окна с одним профилем
подрались бы за файлы профиля.
"""

import asyncio
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import ROOT_DIR, settings
from app.core.errors import AppError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page, Playwright

log = get_logger(__name__)


class BrowserState(StrEnum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    NEEDS_LOGIN = "NEEDS_LOGIN"
    ERROR = "ERROR"


BROWSER_STATE_LABELS: dict[str, str] = {
    BrowserState.STOPPED: "Не запущен",
    BrowserState.STARTING: "Запускается",
    BrowserState.READY: "Готов, вход выполнен",
    BrowserState.NEEDS_LOGIN: "Нужен вход в HH",
    BrowserState.ERROR: "Ошибка",
}


class BrowserManager:
    """Единственный видимый Chromium с постоянным профилем."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._lock = asyncio.Lock()
        self.state: BrowserState = BrowserState.STOPPED
        self.last_error: str | None = None

    @property
    def user_data_dir(self) -> Path:
        raw = settings.browser_user_data_dir
        path = Path(raw)
        return path if path.is_absolute() else (ROOT_DIR / raw).resolve()

    @property
    def is_running(self) -> bool:
        return self._context is not None

    async def start(self) -> BrowserState:
        async with self._lock:
            if self._context is not None:
                return self.state

            self.state = BrowserState.STARTING
            self.last_error = None
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self.user_data_dir.mkdir(parents=True, exist_ok=True)
                # headless запрещён: пользователь должен видеть, что происходит,
                # и иметь возможность вмешаться (§29)
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=False,
                    viewport={"width": 1440, "height": 900},
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except Exception as exc:
                self.state = BrowserState.ERROR
                self.last_error = str(exc)
                await self._cleanup()
                raise AppError(
                    "BROWSER_NOT_STARTED",
                    "Не удалось запустить Chromium. Выполнен ли playwright install chromium?",
                    technical_details=str(exc),
                ) from exc

        return await self.check_auth()

    async def page(self) -> "Page":
        if self._context is None:
            raise AppError("BROWSER_NOT_STARTED", "Браузер не запущен")
        pages = self._context.pages
        return pages[0] if pages else await self._context.new_page()

    async def check_auth(self) -> BrowserState:
        """Определить, вошёл ли пользователь. Ничего не кликаем и не обходим."""
        if self._context is None:
            self.state = BrowserState.STOPPED
            return self.state

        from app.browser.auth import detect_session

        try:
            self.state = await detect_session(await self.page())
        except AppError as exc:
            self.state = BrowserState.ERROR
            self.last_error = exc.human_message
        return self.state

    async def stop(self) -> None:
        async with self._lock:
            await self._cleanup()
            self.state = BrowserState.STOPPED

    async def restart(self) -> BrowserState:
        await self.stop()
        return await self.start()

    async def status(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "label": BROWSER_STATE_LABELS[self.state],
            "is_running": self.is_running,
            "user_data_dir": str(self.user_data_dir),
            "last_error": self.last_error,
        }

    async def _cleanup(self) -> None:
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as exc:
                log.warning("Контекст браузера закрылся с ошибкой: %s", exc)
            self._context = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:
                log.warning("Playwright остановился с ошибкой: %s", exc)
            self._playwright = None


browser = BrowserManager()
