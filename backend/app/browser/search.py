"""Выдача поиска HH: список hh_id и минимум полей, без открытия карточек (§10)."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from app.browser.extract import parse_hh_id
from app.browser.selectors import HH
from app.core.enums import RemoteMode
from app.core.logging import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Page

log = get_logger(__name__)

# Коды опыта HH
EXPERIENCE_CODES = {
    "noExperience": "Нет опыта",
    "between1And3": "1–3 года",
    "between3And6": "3–6 лет",
    "moreThan6": "Более 6 лет",
}


@dataclass(slots=True)
class SearchItem:
    """Строка выдачи. Карточка ещё не открыта, полей минимум."""

    hh_id: str
    url: str
    title: str
    company_name: str | None = None
    salary_text: str | None = None


def build_url(
    query: str,
    *,
    areas: list[str] | None = None,
    experience: list[str] | None = None,
    remote_mode: str = RemoteMode.ANY,
    max_age_days: int | None = None,
    page: int = 0,
    resume_hash: str | None = None,
) -> str:
    """Собрать адрес выдачи. Часть условий отдаём HH, чтобы не тащить
    к себе то, что он и так умеет отфильтровать.

    С resume_hash это лента «Для вас» — рекомендации HH под резюме; текст
    запроса тогда не нужен.
    """
    params: list[tuple[str, str]] = []
    if resume_hash:
        params.append(("resume", resume_hash))
    if query or not resume_hash:
        params.append(("text", query))
    params += [("page", str(page)), ("items_on_page", "50")]
    for area in areas or []:
        params.append(("area", area))
    for level in experience or []:
        params.append(("experience", level))
    if max_age_days:
        params.append(("search_period", str(max_age_days)))
    if remote_mode == RemoteMode.REMOTE_ONLY:
        params.append(("schedule", "remote"))

    return f"{HH.SEARCH_URL}?{urlencode(params)}"


_RESUME_HASH = re.compile(r"/resume/([0-9a-f]{20,})")


def resume_hash_from_url(url: str | None) -> str | None:
    """Идентификатор резюме из ссылки вида hh.kz/resume/4b50d52e…?hhtmFrom=…"""
    match = _RESUME_HASH.search(url or "")
    return match.group(1) if match else None


async def collect_page(page: "Page") -> list[SearchItem]:
    """Собрать строки с одной страницы выдачи."""
    items: list[SearchItem] = []
    cards = page.locator(HH.SEARCH_RESULT_ITEM)

    for index in range(await cards.count()):
        card = cards.nth(index)
        link = card.locator(HH.SEARCH_ITEM_LINK).first
        if not await link.count():
            continue

        href = await link.get_attribute("href") or ""
        hh_id = parse_hh_id(href)
        if not hh_id:
            continue

        items.append(
            SearchItem(
                hh_id=hh_id,
                url=href.split("?")[0],
                title=(await link.inner_text()).strip(),
                company_name=await _optional_text(card, HH.SEARCH_ITEM_COMPANY),
                salary_text=await _optional_text(card, HH.SEARCH_ITEM_SALARY),
            )
        )

    return items


async def has_next_page(page: "Page") -> bool:
    return bool(await page.locator(HH.SEARCH_NEXT_PAGE).count())


async def _optional_text(scope: object, selector: str) -> str | None:
    locator = scope.locator(selector).first  # type: ignore[attr-defined]
    if not await locator.count():
        return None
    return (await locator.inner_text()).strip() or None
