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
    # Быстрый отклик: HH отправил резюме по нажатию «Откликнуться», без формы.
    # Письмо после этого можно только дослать отдельной кнопкой
    sent_on_click: bool = False
    # Отклик невозможен без действия пользователя на HH (например, скрытое резюме)
    blocked_reason: str | None = None


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

    if await page.locator(HH.VACANCY_ARCHIVED).count():
        return ApplyForm(can_apply=False, blocked_reason="Вакансия в архиве")

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
    # Кнопка — ссылка: иногда HH открывает не окно, а отдельную страницу отклика
    await page.wait_for_load_state("domcontentloaded")
    try:
        await page.wait_for_selector(
            f"{HH.SUBMIT_BUTTON}, {HH.RESUME_DELIVERED}, {HH.DIALOG}",
            timeout=20_000,
            state="visible",
        )
    except Exception as exc:
        raise AppError(
            "APPLY_FORM_UNKNOWN",
            "Форма отклика не распознана",
            step="OPEN_APPLY_FORM",
            technical_details=f"{page.url}\n{exc}",
        ) from exc
    # Окно появляется раньше своего содержимого: без паузы форма отклика
    # в окне выглядела бы как предупреждение без кнопки отправки
    await page.wait_for_timeout(1500)

    warning = page.locator(HH.HIDDEN_RESUME_WARNING).first
    if await warning.count() and await warning.is_visible():
        return ApplyForm(
            can_apply=False,
            blocked_reason="Резюме скрыто от этого работодателя: поменяйте видимость резюме на HH",
        )

    submit_visible = await page.locator(HH.SUBMIT_BUTTON).first.is_visible()
    if not submit_visible and not await page.locator(HH.RESUME_DELIVERED).count():
        # Окно HH без формы — предупреждение вроде «вакансия в другой стране,
        # скорее всего будет отказ». Соглашаться за пользователя бот не вправе
        dialog_text = (await page.locator(HH.DIALOG).first.inner_text()).strip()
        # Капча — не причина пропустить вакансию, а сигнал остановиться: HH
        # покажет её и на следующей. Проходит её человек, бот не трогает (§7)
        if "капч" in dialog_text.lower() or await page.locator(HH.CAPTCHA).count():
            raise AppError(
                "HH_CAPTCHA",
                "HH показал капчу. Пройдите её сами в окне браузера и нажмите «Продолжить»",
                step="OPEN_APPLY_FORM",
                technical_details=dialog_text[:500],
            )
        abort = page.locator(HH.WARNING_ABORT).first
        if await abort.count() and await abort.is_visible():
            await abort.click()
        else:
            await page.keyboard.press("Escape")
        return ApplyForm(
            can_apply=False,
            blocked_reason="HH предупредил: " + " ".join(dialog_text.split())[:200],
        )

    if not await page.locator(HH.SUBMIT_BUTTON).count():
        # Формы нет, а резюме уже доставлено — это быстрый отклик
        return ApplyForm(can_apply=True, sent_on_click=True)

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

    # HH хранит черновик письма: без очистки текст допечатывался к старому
    await field.fill("")
    await field.click()
    await field.type(
        letter,
        delay=delay_per_char_ms,
        timeout=typing_timeout_ms(len(letter), delay_per_char_ms),
    )

    typed = await field.input_value()
    if not letters_match(letter, typed):
        raise AppError(
            "LETTER_MISMATCH",
            "Текст в поле письма не совпал с письмом — отклик не отправлен",
            step="TYPE_LETTER",
            technical_details=typed[:2000],
        )


async def dismiss_dialogs(page: "Page") -> None:
    """Закрыть всплывающие окна после быстрого отклика («Какой формат удобнее?»).

    Escape закрывает опрос без ответа: настройки поиска в HH не меняются.
    Первый Escape — безусловно: разметка опроса может и не быть role=dialog.
    """
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(500)
    for _ in range(3):
        if not await page.locator(HH.DIALOG).count():
            return
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)


async def send_letter_after_apply(page: "Page") -> bool:
    """Отправить письмо, уже введённое в поле под «Резюме доставлено».

    True — кнопка исчезла после нажатия, то есть HH письмо принял.
    """
    button = page.locator(HH.LETTER_SUBMIT_AFTER_APPLY).first
    if not await button.count():
        raise AppError(
            "BROWSER_SELECTOR_NOT_FOUND",
            "Кнопка отправки письма после отклика не найдена",
            step="SEND_LETTER",
        )
    await button.click()
    try:
        await button.wait_for(state="hidden", timeout=15_000)
    except Exception as exc:
        log.warning("После отправки письма кнопка не исчезла: %s", exc)
        return False
    return True


def typing_timeout_ms(chars: int, delay_per_char_ms: float) -> float:
    """Посимвольный ввод письма на 800 символов идёт дольше стандартных 30 секунд
    Playwright. Запас на собственную задержку браузера на каждый символ."""
    return chars * (delay_per_char_ms + 50) + 15_000


def letters_match(expected: str, actual: str) -> bool:
    """Сравнение без учёта переводов строк Windows и пробелов по краям."""

    def normalize(text: str) -> str:
        return text.replace("\r\n", "\n").strip()

    return normalize(expected) == normalize(actual)


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
