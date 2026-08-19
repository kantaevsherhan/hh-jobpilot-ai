"""Определение состояния сессии HH.

Капча, SMS и любое подтверждение не обходятся и не прокликиваются:
бот сообщает, что нужно действие пользователя, и останавливается (§9).
"""

from typing import TYPE_CHECKING

from app.browser.selectors import HH
from app.core.errors import AppError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Page

    from app.browser.manager import BrowserState

log = get_logger(__name__)


async def detect_session(page: "Page") -> "BrowserState":
    from app.browser.manager import BrowserState

    try:
        if not page.url.startswith(HH.BASE_URL):
            await page.goto(HH.BASE_URL, wait_until="domcontentloaded", timeout=30_000)
        else:
            await page.reload(wait_until="domcontentloaded", timeout=30_000)
    except Exception as exc:
        raise AppError(
            "BROWSER_TIMEOUT",
            "hh.kz не открылся. Проверьте интернет.",
            technical_details=str(exc),
        ) from exc

    if await page.locator(HH.CAPTCHA).count():
        raise AppError(
            "HH_CAPTCHA",
            "HH показал капчу. Пройдите её в открытом окне браузера и нажмите «Проверить снова».",
            recoverable=True,
        )

    if await page.locator(HH.LOGGED_IN).count():
        return BrowserState.READY

    return BrowserState.NEEDS_LOGIN
