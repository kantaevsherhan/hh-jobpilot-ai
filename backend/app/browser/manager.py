"""Запуск Chromium и состояние сессии HH (§9).

Браузер один на всё приложение: два видимых окна с одним профилем
подрались бы за файлы профиля.
"""

import asyncio
import os
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import ROOT_DIR, settings
from app.core.errors import AppError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page, Playwright

log = get_logger(__name__)


def _windows_browser_channel() -> str | None:
    """На Windows предпочитать установленный Chrome/Edge браузеру из Playwright."""
    if os.name != "nt":
        return None

    program_files = [
        Path(value)
        for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
        if (value := os.environ.get(key))
    ]
    for channel, relative_path in (
        ("chrome", Path("Google/Chrome/Application/chrome.exe")),
        ("msedge", Path("Microsoft/Edge/Application/msedge.exe")),
    ):
        if any((root / relative_path).is_file() for root in program_files):
            return channel
    return None


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
                channel = _windows_browser_channel()
                # headless запрещён: пользователь должен видеть, что происходит,
                # и иметь возможность вмешаться (§29)
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    channel=channel,
                    headless=False,
                    viewport={"width": 1440, "height": 900},
                    args=["--disable-blink-features=AutomationControlled"],
                )
                # Пользователь может закрыть окно руками в любой момент — тогда
                # состояние должно стать «не запущен», а не «ошибка сети»
                self._context.on("close", self._on_context_closed)
            except Exception as exc:
                self.state = BrowserState.ERROR
                self.last_error = str(exc)
                await self._cleanup()
                raise AppError(
                    "BROWSER_NOT_STARTED",
                    "Не удалось открыть браузер. На Windows проверьте установку Chrome или Edge. "
                    "На других системах выполните playwright install chromium.",
                    technical_details=str(exc),
                ) from exc

        return await self.check_auth()

    def _on_context_closed(self, _: object = None) -> None:
        self._context = None
        if self.state != BrowserState.STOPPED:
            self.state = BrowserState.STOPPED
            log.info("Окно браузера закрыто")

    async def page(self) -> "Page":
        if self._context is None:
            raise AppError(
                "BROWSER_NOT_STARTED",
                "Браузер не запущен. Откройте «Настройки → Браузер» и нажмите «Запустить».",
            )
        pages = [page for page in self._context.pages if not page.is_closed()]
        if pages:
            return pages[0]
        try:
            return await self._context.new_page()
        except Exception as exc:
            # Окно закрыли, пока шёл прогон
            self._on_context_closed()
            raise AppError(
                "BROWSER_NOT_STARTED",
                "Окно браузера закрыто. Запустите его заново.",
                technical_details=str(exc),
            ) from exc

    async def check_auth(self) -> BrowserState:
        """Определить, вошёл ли пользователь. Ничего не кликаем и не обходим."""
        if self._context is None:
            self.state = BrowserState.STOPPED
            return self.state

        from app.browser.auth import detect_session

        try:
            self.state = await detect_session(await self.page())
        except AppError as exc:
            if exc.error_code == "BROWSER_NOT_STARTED":
                self.state = BrowserState.STOPPED
            else:
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
