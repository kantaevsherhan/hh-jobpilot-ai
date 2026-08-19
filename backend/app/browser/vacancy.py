"""Открытие карточки вакансии."""

from typing import TYPE_CHECKING

from app.browser import extract
from app.browser.extract import VacancyData
from app.browser.selectors import HH
from app.core.errors import AppError

if TYPE_CHECKING:
    from playwright.async_api import Page


def vacancy_url(hh_id: str) -> str:
    return f"{HH.BASE_URL}/vacancy/{hh_id}"


async def open_and_extract(page: "Page", hh_id: str) -> VacancyData:
    url = vacancy_url(hh_id)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    except Exception as exc:
        raise AppError(
            "BROWSER_TIMEOUT",
            f"Страница вакансии {hh_id} не открылась",
            technical_details=str(exc),
        ) from exc

    if await page.locator(HH.CAPTCHA).count():
        raise AppError("HH_CAPTCHA", "HH показал капчу. Пройдите её в открытом окне браузера.")

    return await extract.extract(page, url)
