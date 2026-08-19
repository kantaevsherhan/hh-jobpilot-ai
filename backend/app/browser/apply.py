"""Форма отклика на HH (§21).

Ни одна из этих функций не решает, можно ли отправлять: это проверяется
до вызова, в pipeline. Здесь только работа со страницей.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.browser.selectors import HH
from app.core.errors import AppError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Page

log = get_logger(__name__)


@dataclass(slots=True)
class ApplyForm:
    """Что удалось увидеть на странице перед отправкой."""

    can_apply: bool
    already_applied: bool = False
    is_external: bool = False
    has_letter_field: bool = False
    questions: list[str] | None = None


async def inspect(page: "Page", hh_id: str) -> ApplyForm:
    """Осмотреть страницу вакансии перед откликом."""
    if hh_id not in page.url:
        raise AppError(
            "HH_UNKNOWN_PAGE",
            "Открыта не та страница: номер вакансии в адресе не совпадает",
            technical_details=page.url,
        )

    if await page.locator(HH.ALREADY_APPLIED).count():
        return ApplyForm(can_apply=False, already_applied=True)

    if await page.locator(HH.EXTERNAL_APPLY).count():
        return ApplyForm(can_apply=False, is_external=True)

    if not await page.locator(HH.APPLY_BUTTON).count():
        return ApplyForm(can_apply=False)

    return ApplyForm(can_apply=True)


async def open_form(page: "Page") -> ApplyForm:
    """Нажать «Откликнуться» и осмотреть форму."""
    button = page.locator(HH.APPLY_BUTTON).first
    if not await button.count():
        raise AppError(
            "BROWSER_SELECTOR_NOT_FOUND",
            "Не найдена кнопка отклика. Возможно, HH изменил вёрстку.",
            step="OPEN_APPLY_FORM",
        )

    await button.click()
    try:
        await page.wait_for_selector(
            f"{HH.LETTER_FIELD}, {HH.SUBMIT_BUTTON}", timeout=15_000, state="visible"
        )
    except Exception as exc:
        raise AppError(
            "APPLY_FORM_UNKNOWN",
            "Форма отклика не распознана",
            step="OPEN_APPLY_FORM",
            technical_details=str(exc),
        ) from exc

    questions = await _read_questions(page)
    return ApplyForm(
        can_apply=True,
        has_letter_field=bool(await page.locator(HH.LETTER_FIELD).count()),
        questions=questions,
    )


async def type_letter(page: "Page", letter: str, delay_per_char_ms: float) -> None:
    """Письмо вводится посимвольно, а не вставляется одним fill (§20)."""
    field = page.locator(HH.LETTER_FIELD).first
    if not await field.count():
        toggle = page.locator(HH.LETTER_TOGGLE).first
        if await toggle.count():
            await toggle.click()
            field = page.locator(HH.LETTER_FIELD).first
    if not await field.count():
        raise AppError(
            "BROWSER_SELECTOR_NOT_FOUND",
            "Поле сопроводительного письма не найдено",
            step="TYPE_LETTER",
        )

    await field.click()
    await field.type(letter, delay=delay_per_char_ms)


async def submit(page: "Page") -> bool:
    """Нажать отправку и дождаться подтверждения.

    Возвращает True только если подтверждение реально появилось на странице.
    Ретрай сетевой ошибки никогда не повторяет нажатие вслепую (§21).
    """
    button = page.locator(HH.SUBMIT_BUTTON).first
    if not await button.count():
        raise AppError(
            "BROWSER_SELECTOR_NOT_FOUND",
            "Кнопка отправки отклика не найдена",
            step="SUBMIT_APPLICATION",
        )

    await button.click()
    try:
        await page.wait_for_selector(HH.APPLY_SUCCESS, timeout=30_000, state="visible")
    except Exception as exc:
        log.warning("Подтверждение отклика не появилось: %s", exc)
        return False
    return True


async def _read_questions(page: "Page") -> list[str]:
    items = page.locator(HH.QUESTION_ITEM)
    return [(await items.nth(i).inner_text()).strip() for i in range(await items.count())]
