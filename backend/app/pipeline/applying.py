"""Отправка отклика и защита от дублей (§21).

Порядок проверок здесь не декоративный: каждая из них отсекает свой
способ отправить второй отклик.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ErrorCode, RuntimeMode, VacancyStatus
from app.core.logging import get_logger
from app.storage.models import Application, Vacancy
from app.storage.models.base import utcnow

if TYPE_CHECKING:
    from playwright.async_api import Page

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ApplyGuard:
    """Итог проверок «можно ли жать отправку»."""

    allowed: bool
    status: VacancyStatus | None = None
    error_code: str | None = None
    message: str | None = None


async def applications_today(session: AsyncSession, now: datetime | None = None) -> int:
    """Счёт за календарные сутки: переживает перезапуск и не сбрасывается
    новым прогоном (§20).

    Сутки считаются по местному времени пользователя, а не по UTC:
    приложение локальное, и «сегодня» для него — это его же календарь.
    """
    moment = now or datetime.now(UTC)
    local_midnight = moment.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    start = local_midnight.astimezone(UTC)
    return (
        await session.scalar(
            select(func.count()).select_from(Application).where(Application.applied_at >= start)
        )
    ) or 0


async def check_can_apply(
    session: AsyncSession,
    *,
    vacancy_id: int,
    runtime_mode: str,
    applications_in_run: int = 0,
    max_per_run: int = 20,
    max_per_day: int = 30,
    fact_check_passed: bool | None = None,
    now: datetime | None = None,
) -> ApplyGuard:
    existing = await session.scalar(select(Application).where(Application.vacancy_id == vacancy_id))
    if existing is not None:
        return ApplyGuard(
            False,
            VacancyStatus.APPLIED,
            "DUPLICATE",
            "Отклик на эту вакансию уже отправлялся",
        )

    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None:
        return ApplyGuard(False, None, "NOT_FOUND", "Вакансия не найдена")
    if vacancy.is_closed:
        return ApplyGuard(
            False, VacancyStatus.VACANCY_CLOSED, "VACANCY_CLOSED", "Вакансия закрыта на HH"
        )

    if fact_check_passed is False:
        return ApplyGuard(
            False,
            VacancyStatus.REVIEW_REQUIRED,
            ErrorCode.FACT_CHECK_FAILED,
            "Проверка фактов не пройдена, автоотклик запрещён",
        )

    if applications_in_run >= max_per_run:
        return ApplyGuard(
            False, None, ErrorCode.LIMIT_REACHED, f"Достигнут лимит за прогон: {max_per_run}"
        )

    today = await applications_today(session, now)
    if today >= max_per_day:
        return ApplyGuard(
            False, None, ErrorCode.LIMIT_REACHED, f"Достигнут дневной лимит: {max_per_day}"
        )

    if runtime_mode != RuntimeMode.LIVE:
        return ApplyGuard(
            False,
            VacancyStatus.APPLY_PREPARED,
            None,
            "Режим DRY_RUN: всё готово, но отправка запрещена режимом",
        )

    return ApplyGuard(True)


async def record_application(
    session: AsyncSession,
    *,
    vacancy_id: int,
    resume_id: int,
    letter_id: int | None = None,
    run_id: int | None = None,
    hh_status: str | None = None,
    error_code: str | None = None,
    screenshot_path: str | None = None,
    answers: dict[str, Any] | None = None,
) -> Application:
    """Записать отклик. Уникальность vacancy_id на уровне схемы — последняя
    линия защиты, если проверки выше кто-то обойдёт."""
    application = Application(
        vacancy_id=vacancy_id,
        resume_id=resume_id,
        letter_id=letter_id,
        run_id=run_id,
        applied_at=utcnow(),
        hh_status=hh_status,
        error_code=error_code,
        screenshot_path=screenshot_path,
        answers_json=answers,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


async def stale_applications(session: AsyncSession, days: int = 60) -> list[Application]:
    """Отклики, статусы которых стоит пересинхронизировать (§23)."""
    since = datetime.now(UTC) - timedelta(days=days)
    rows = await session.scalars(
        select(Application).where(Application.applied_at >= since).order_by(Application.id)
    )
    return list(rows.all())


async def submit_on_page(page: "Page", hh_id: str) -> tuple[bool, str | None]:
    """Нажать отправку. Возвращает (успех, код ошибки).

    Если после нажатия результат неизвестен — это не «повторить», а
    APPLICATION_STATE_UNKNOWN и ручная проверка (§21).
    """
    from app.browser import apply as apply_page

    try:
        confirmed = await apply_page.submit(page)
    except Exception as exc:
        log.warning("Отправка отклика на %s не завершилась: %s", hh_id, exc)
        return False, ErrorCode.APPLICATION_STATE_UNKNOWN

    if not confirmed:
        return False, ErrorCode.APPLICATION_STATE_UNKNOWN
    return True, None
