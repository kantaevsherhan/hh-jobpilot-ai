"""Отклики: список, ручная отправка, синхронизация статусов (§21, §23)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import Session
from app.browser import apply as apply_page
from app.browser import vacancy as vacancy_page
from app.browser.manager import browser
from app.core.enums import RuntimeMode, VacancyStatus
from app.core.errors import ConflictError
from app.pipeline import applying
from app.pipeline.delays import Delays
from app.storage.models import Application, Letter, Resume, Vacancy
from app.storage.repositories import crud
from app.storage.repositories import settings as settings_repo
from app.storage.repositories import vacancies as repo

router = APIRouter(tags=["Отклики"])


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vacancy_id: int
    resume_id: int
    letter_id: int | None
    applied_at: datetime
    hh_status: str | None
    hh_status_checked_at: datetime | None
    error_code: str | None


class ApplicationRow(ApplicationOut):
    vacancy_title: str = ""
    vacancy_url: str = ""
    company_name: str | None = None


@router.get("/applications", response_model=list[ApplicationRow], summary="История откликов")
async def list_applications(session: Session, resume_id: int | None = None) -> list[ApplicationRow]:
    query = select(Application, Vacancy).join(Vacancy, Vacancy.id == Application.vacancy_id)
    if resume_id is not None:
        query = query.where(Application.resume_id == resume_id)
    rows = await session.execute(query.order_by(Application.applied_at.desc()))

    return [
        ApplicationRow.model_validate(
            ApplicationOut.model_validate(application).model_dump()
            | {
                "vacancy_title": vacancy.title,
                "vacancy_url": vacancy.url,
                "company_name": vacancy.company_name,
            }
        )
        for application, vacancy in rows.all()
    ]


class ApplyRequest(BaseModel):
    resume_id: int
    letter_id: int | None = None
    runtime_mode: RuntimeMode = RuntimeMode.DRY_RUN


@router.post("/vacancies/{vacancy_id}/apply", summary="Откликнуться вручную")
async def apply_manually(
    vacancy_id: int, payload: ApplyRequest, session: Session
) -> dict[str, Any]:
    """Ручной отклик проходит те же проверки §21, что и автоматический."""
    resume = await crud.get_or_404(session, Resume, payload.resume_id, "Резюме")
    vacancy = await crud.get_or_404(session, Vacancy, vacancy_id, "Вакансия")
    letter = await session.get(Letter, payload.letter_id) if payload.letter_id else None

    app_settings = await settings_repo.get_all(session)
    limits = app_settings.get("limits", {})
    delays = Delays(app_settings.get("delays"))

    guard = await applying.check_can_apply(
        session,
        vacancy_id=vacancy_id,
        runtime_mode=payload.runtime_mode.value,
        max_per_run=int(limits.get("max_applications_per_run", 20)),
        max_per_day=int(limits.get("max_applications_per_day", 30)),
        fact_check_passed=letter.fact_check_passed if letter else None,
    )

    if not guard.allowed and guard.status != VacancyStatus.APPLY_PREPARED:
        raise ConflictError(guard.error_code or "APPLY_BLOCKED", guard.message or "Отклик запрещён")

    if not browser.is_running:
        raise ConflictError(
            "BROWSER_NOT_STARTED", "Браузер не запущен. Откройте «Настройки → Браузер»."
        )

    page = await browser.page()
    await page.goto(vacancy_page.vacancy_url(vacancy.hh_id), wait_until="domcontentloaded")
    await delays.pause("page_load")

    state = await apply_page.inspect(page, vacancy.hh_id)
    if state.already_applied:
        await applying.record_application(
            session,
            vacancy_id=vacancy_id,
            resume_id=resume.id,
            hh_status="SENT",
            error_code="ALREADY_APPLIED",
        )
        await repo.ensure_decision(
            session, resume.id, vacancy_id, status=VacancyStatus.APPLIED.value
        )
        return {"status": VacancyStatus.APPLIED.value, "message": "На HH уже есть отклик"}

    if state.is_external:
        await repo.ensure_decision(
            session, resume.id, vacancy_id, status=VacancyStatus.EXTERNAL_APPLY.value
        )
        return {"status": VacancyStatus.EXTERNAL_APPLY.value, "message": "Отклик на внешнем сайте"}

    await delays.pause("before_open_form")
    form = await apply_page.open_form(page)

    if form.has_letter_field and letter:
        await apply_page.type_letter(page, letter.content, delays.seconds("typing_per_char") * 1000)

    # DRY_RUN доходит до формы и останавливается: кнопка не нажимается (§20)
    if payload.runtime_mode != RuntimeMode.LIVE:
        await repo.ensure_decision(
            session, resume.id, vacancy_id, status=VacancyStatus.APPLY_PREPARED.value
        )
        return {
            "status": VacancyStatus.APPLY_PREPARED.value,
            "message": "Форма заполнена в пробном режиме. Отклик не отправлен",
        }

    await delays.pause("before_submit")
    ok, error_code = await applying.submit_on_page(page, vacancy.hh_id)

    await applying.record_application(
        session,
        vacancy_id=vacancy_id,
        resume_id=resume.id,
        letter_id=letter.id if letter else None,
        hh_status="SENT" if ok else None,
        error_code=error_code,
    )
    status = VacancyStatus.APPLIED if ok else VacancyStatus.APPLY_UNKNOWN
    await repo.ensure_decision(session, resume.id, vacancy_id, status=status.value)

    return {
        "status": status.value,
        "message": "Отклик отправлен" if ok else "Подтверждение не получено, проверьте вручную",
    }


@router.post("/applications/sync-status", summary="Обновить статусы откликов")
async def sync_statuses(session: Session, days: int = 60) -> dict[str, int]:
    """Пока читаем только то, что уже знаем: страницу откликов открывает
    отдельная задача прогона. Здесь — пересчёт по базе (§23)."""
    rows = await applying.stale_applications(session, days)
    return {"checked": len(rows)}
