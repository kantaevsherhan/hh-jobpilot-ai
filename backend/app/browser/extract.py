"""Извлечение данных вакансии со страницы (§10).

Основной путь — встроенный в страницу JSON: он устойчивее CSS-классов,
которые меняются каждый релиз HH. Фолбэк — DOM-селекторы. Наружу оба
пути отдают одну и ту же модель.
"""

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.browser.selectors import HH
from app.core.enums import WorkFormat
from app.core.errors import AppError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Page

log = get_logger(__name__)

# Казахские специфические буквы — по ним отличаем kk от ru (§11)
KAZAKH_LETTERS = set("әғқңөұүһі")
CYRILLIC = re.compile(r"[а-яёәғқңөұүһі]", re.IGNORECASE)
LATIN = re.compile(r"[a-z]", re.IGNORECASE)


class VacancyData(BaseModel):
    """То, что удалось прочитать со страницы вакансии."""

    hh_id: str
    url: str
    title: str
    company_hh_id: str | None = None
    company_name: str | None = None
    description: str = ""
    description_lang: str | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    currency: str | None = None
    salary_gross: bool | None = None
    work_format: str | None = None
    experience: str | None = None
    employment: str | None = None
    schedule: str | None = None
    area: str | None = None
    published_at: datetime | None = None
    is_closed: bool = False
    raw_json: dict[str, Any] = Field(default_factory=dict)


def detect_language(text: str) -> str:
    """Язык описания определяется кодом, а не моделью (§11).

    По языку не фильтруем — он нужен только чтобы выбрать язык письма.
    """
    sample = text[:4000].lower()
    if not sample.strip():
        return "ru"
    if any(letter in sample for letter in KAZAKH_LETTERS):
        return "kk"
    cyrillic = len(CYRILLIC.findall(sample))
    latin = len(LATIN.findall(sample))
    if cyrillic == 0 and latin == 0:
        return "ru"
    return "ru" if cyrillic >= latin else "en"


def detect_work_format(*sources: str | None) -> str:
    """Формат работы по тексту: HH называет его по-разному в разных полях."""
    text = " ".join(s.lower() for s in sources if s)
    if not text:
        return WorkFormat.UNKNOWN
    if "гибрид" in text:
        return WorkFormat.HYBRID
    if "удал" in text or "remote" in text or "из дома" in text:
        return WorkFormat.REMOTE
    if "офис" in text or "office" in text or "на месте" in text:
        return WorkFormat.OFFICE
    return WorkFormat.UNKNOWN


def parse_hh_id(url: str) -> str | None:
    match = re.search(r"/vacancy/(\d+)", url)
    return match.group(1) if match else None


def from_json(payload: dict[str, Any], url: str) -> VacancyData | None:
    """Собрать вакансию из встроенного объекта страницы."""
    vacancy = _find_vacancy_object(payload)
    if vacancy is None:
        return None

    hh_id = str(vacancy.get("vacancyId") or vacancy.get("id") or parse_hh_id(url) or "")
    if not hh_id:
        return None

    salary = vacancy.get("compensation") or vacancy.get("salary") or {}
    employer = vacancy.get("company") or vacancy.get("employer") or {}
    description = _strip_html(str(vacancy.get("description") or ""))

    return VacancyData(
        hh_id=hh_id,
        url=url,
        title=str(vacancy.get("name") or vacancy.get("title") or ""),
        company_hh_id=_str_or_none(employer.get("id")),
        company_name=_str_or_none(employer.get("name")),
        description=description,
        description_lang=detect_language(description),
        salary_from=_int_or_none(salary.get("from")),
        salary_to=_int_or_none(salary.get("to")),
        currency=_str_or_none(salary.get("currencyCode") or salary.get("currency")),
        salary_gross=salary.get("gross") if isinstance(salary.get("gross"), bool) else None,
        work_format=detect_work_format(
            _nested_name(vacancy, "workFormat"),
            _nested_name(vacancy, "schedule"),
            _nested_name(vacancy, "workingTimeModes"),
            description[:1500],
        ),
        experience=_nested_name(vacancy, "experience"),
        employment=_nested_name(vacancy, "employment"),
        schedule=_nested_name(vacancy, "schedule"),
        area=_nested_name(vacancy, "area"),
        published_at=_parse_date(vacancy.get("publicationDate") or vacancy.get("publishedAt")),
        is_closed=bool(vacancy.get("archived") or vacancy.get("isArchived")),
        raw_json=vacancy if len(str(vacancy)) < 200_000 else {},
    )


async def extract(page: "Page", url: str) -> VacancyData:
    """JSON → не вышло → DOM → не вышло → PARSE_FAILED (§10)."""
    payload = await _read_page_state(page)
    if payload:
        data = from_json(payload, url)
        if data and data.title:
            return data
        log.info("JSON на странице есть, но вакансия из него не собралась, пробую DOM")

    return await _from_dom(page, url)


async def _read_page_state(page: "Page") -> dict[str, Any] | None:
    from app.browser.selectors import TEMPLATE_STATE_KEYS

    try:
        result: Any = await page.evaluate(
            """(keys) => {
                const state = window.templateVars || {};
                for (const key of keys) {
                    if (window[key]) return window[key];
                    if (state[key]) return state[key];
                }
                return Object.keys(state).length ? state : null;
            }""",
            list(TEMPLATE_STATE_KEYS),
        )
    except Exception as exc:
        log.info("Встроенный JSON не прочитался: %s", exc)
        return None
    return result if isinstance(result, dict) else None


async def _from_dom(page: "Page", url: str) -> VacancyData:
    hh_id = parse_hh_id(url) or parse_hh_id(page.url)
    if not hh_id:
        raise AppError("PARSE_FAILED", "В адресе страницы нет номера вакансии")

    title = await _text(page, HH.VACANCY_TITLE)
    if not title:
        raise AppError(
            "PARSE_FAILED",
            "Не удалось прочитать вакансию: ни встроенный JSON, ни разметка не подошли",
            technical_details=url,
        )

    description = await _text(page, HH.VACANCY_DESCRIPTION)
    salary_text = await _text(page, HH.VACANCY_SALARY)
    salary_from, salary_to, currency, gross = _parse_salary_text(salary_text)
    experience = await _text(page, HH.VACANCY_EXPERIENCE)
    employment = await _text(page, HH.VACANCY_EMPLOYMENT)

    return VacancyData(
        hh_id=hh_id,
        url=url,
        title=title,
        company_name=await _text(page, HH.VACANCY_COMPANY) or None,
        description=description,
        description_lang=detect_language(description),
        salary_from=salary_from,
        salary_to=salary_to,
        currency=currency,
        salary_gross=gross,
        work_format=detect_work_format(employment, description[:1500]),
        experience=experience or None,
        employment=employment or None,
        area=await _text(page, HH.VACANCY_ADDRESS) or None,
        is_closed=bool(await page.locator(HH.VACANCY_ARCHIVED).count()),
    )


CURRENCY_BY_SIGN = {
    "₸": "KZT",
    "тг": "KZT",
    "₽": "RUR",
    "руб": "RUR",
    "$": "USD",
    "€": "EUR",
}


def _parse_salary_text(text: str) -> tuple[int | None, int | None, str | None, bool | None]:
    """Разобрать «от 700 000 до 900 000 ₸ на руки»."""
    if not text:
        return None, None, None, None

    lowered = text.lower().replace("\xa0", " ")
    numbers = [int(n.replace(" ", "")) for n in re.findall(r"\d[\d ]{2,}", lowered)]

    salary_from = salary_to = None
    if "от" in lowered and "до" in lowered and len(numbers) >= 2:
        salary_from, salary_to = numbers[0], numbers[1]
    elif "от" in lowered and numbers:
        salary_from = numbers[0]
    elif "до" in lowered and numbers:
        salary_to = numbers[0]
    elif len(numbers) >= 2:
        salary_from, salary_to = numbers[0], numbers[1]
    elif numbers:
        salary_from = numbers[0]

    currency = next((code for sign, code in CURRENCY_BY_SIGN.items() if sign in lowered), None)

    gross: bool | None = None
    if "на руки" in lowered:
        gross = False
    elif "до вычета" in lowered or "gross" in lowered:
        gross = True

    return salary_from, salary_to, currency, gross


def _find_vacancy_object(payload: dict[str, Any], depth: int = 0) -> dict[str, Any] | None:
    """Найти объект вакансии в дереве состояния страницы.

    HH меняет структуру, поэтому ищем по набору характерных ключей,
    а не по фиксированному пути.
    """
    if depth > 6:
        return None
    if _looks_like_vacancy(payload):
        return payload
    for value in payload.values():
        if isinstance(value, dict):
            found = _find_vacancy_object(value, depth + 1)
            if found:
                return found
        elif isinstance(value, list):
            for item in value[:20]:
                if isinstance(item, dict):
                    found = _find_vacancy_object(item, depth + 1)
                    if found:
                        return found
    return None


def _looks_like_vacancy(obj: dict[str, Any]) -> bool:
    has_id = "vacancyId" in obj or "id" in obj
    has_name = "name" in obj or "title" in obj
    has_body = "description" in obj or "compensation" in obj or "employer" in obj
    return has_id and has_name and has_body


def _strip_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</li>", "\n", html)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def _text(page: "Page", selector: str) -> str:
    locator = page.locator(selector).first
    if not await locator.count():
        return ""
    return (await locator.inner_text()).strip()


def _str_or_none(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _nested_name(obj: dict[str, Any], key: str) -> str | None:
    value = obj.get(key)
    if isinstance(value, dict):
        return _str_or_none(value.get("name") or value.get("title"))
    if isinstance(value, list) and value:
        first = value[0]
        return _str_or_none(first.get("name") if isinstance(first, dict) else first)
    return _str_or_none(value)


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=UTC)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
