"""Вакансии: таблица с серверной пагинацией, карточка и действия (§26, §27)."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, func, or_, select

from app.api.deps import Session
from app.core.enums import VacancyStatus
from app.core.errors import NotFoundError
from app.filters.suspicious import check_suspicious
from app.storage.models import Application, Letter, Resume, ResumeVacancy, Vacancy
from app.storage.models.base import utcnow
from app.storage.repositories import crud
from app.storage.repositories import vacancies as repo

router = APIRouter(prefix="/vacancies", tags=["Вакансии"])


class VacancyRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hh_id: str
    url: str
    title: str
    company_name: str | None
    salary_from: int | None
    salary_to: int | None
    currency: str | None
    salary_gross: bool | None
    work_format: str | None
    experience: str | None
    area: str | None
    published_at: datetime | None
    first_seen_at: datetime
    is_closed: bool

    status: str | None = None
    skip_reason: str | None = None
    skip_details: str | None = None
    score: int | None = None
    is_suspicious: bool = False
    hidden_instructions: list[Any] = []
    decision_id: int | None = None
    applied_at: datetime | None = None


class VacancyPage(BaseModel):
    items: list[VacancyRow]
    total: int


class VacancyDetail(VacancyRow):
    description: str = ""
    description_lang: str | None = None
    analysis_json: dict[str, Any] | None = None
    suspicious_reasons: list[Any] = []


def _row(
    vacancy: Vacancy, decision: ResumeVacancy | None, applied_at: datetime | None
) -> dict[str, Any]:
    data = VacancyRow.model_validate(vacancy).model_dump()
    if decision is not None:
        data |= {
            "status": decision.status,
            "skip_reason": decision.skip_reason,
            "skip_details": decision.skip_details,
            "score": decision.score,
            "is_suspicious": decision.is_suspicious,
            "hidden_instructions": list(decision.hidden_instructions),
            "decision_id": decision.id,
        }
    data["applied_at"] = applied_at
    return data


def _base_query(resume_id: int) -> Select[Any]:
    return (
        select(Vacancy, ResumeVacancy, Application.applied_at)
        .join(
            ResumeVacancy,
            (ResumeVacancy.vacancy_id == Vacancy.id) & (ResumeVacancy.resume_id == resume_id),
            isouter=True,
        )
        .join(Application, Application.vacancy_id == Vacancy.id, isouter=True)
    )


@router.get("", response_model=VacancyPage, summary="Вакансии с фильтрами")
async def list_vacancies(
    session: Session,
    resume_id: int,
    search: str | None = None,
    status: Annotated[list[str] | None, Query()] = None,
    min_score: int | None = None,
    min_salary: int | None = None,
    work_format: str | None = None,
    company: str | None = None,
    only_suspicious: bool = False,
    page: int = 1,
    per_page: int = 25,
) -> VacancyPage:
    query = _base_query(resume_id)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Vacancy.title).like(pattern),
                func.lower(Vacancy.company_name).like(pattern),
            )
        )
    if status:
        query = query.where(ResumeVacancy.status.in_(status))
    if min_score is not None:
        query = query.where(ResumeVacancy.score >= min_score)
    if min_salary is not None:
        query = query.where(Vacancy.salary_from >= min_salary)
    if work_format:
        query = query.where(Vacancy.work_format == work_format)
    if company:
        query = query.where(func.lower(Vacancy.company_name).like(f"%{company.lower()}%"))
    if only_suspicious:
        query = query.where(ResumeVacancy.is_suspicious)

    total = (await session.scalar(select(func.count()).select_from(query.subquery()))) or 0

    rows = await session.execute(
        query.order_by(Vacancy.first_seen_at.desc(), Vacancy.id.desc())
        .offset(max(0, page - 1) * per_page)
        .limit(per_page)
    )

    items = [
        VacancyRow.model_validate(_row(vacancy, decision, applied_at))
        for vacancy, decision, applied_at in rows.all()
    ]
    return VacancyPage(items=items, total=total)


@router.get("/{vacancy_id}", response_model=VacancyDetail, summary="Карточка вакансии")
async def get_vacancy(vacancy_id: int, resume_id: int, session: Session) -> VacancyDetail:
    row = (await session.execute(_base_query(resume_id).where(Vacancy.id == vacancy_id))).first()
    if row is None:
        raise NotFoundError("Вакансия")
    vacancy, decision, applied_at = row

    data = _row(vacancy, decision, applied_at)
    data |= {
        "description": vacancy.description,
        "description_lang": vacancy.description_lang,
        "analysis_json": (decision.analysis_json or {}).get("parsed") if decision else None,
        "suspicious_reasons": list(decision.suspicious_reasons) if decision else [],
    }
    return VacancyDetail.model_validate(data)


@router.post("/{vacancy_id}/skip", summary="Пропустить вручную")
async def skip(vacancy_id: int, resume_id: int, session: Session) -> dict[str, str]:
    await repo.ensure_decision(
        session,
        resume_id,
        vacancy_id,
        status=VacancyStatus.SKIPPED_BY_USER.value,
        decided_at=utcnow(),
    )
    return {"status": VacancyStatus.SKIPPED_BY_USER.value}


@router.post("/{vacancy_id}/unmark-suspicious", summary="Это нормальная вакансия")
async def unmark_suspicious(vacancy_id: int, resume_id: int, session: Session) -> dict[str, str]:
    """Флаг снимается, вакансия возвращается в общий поток (§13)."""
    await repo.ensure_decision(
        session,
        resume_id,
        vacancy_id,
        status=VacancyStatus.REVIEW_REQUIRED.value,
        is_suspicious=False,
        suspicious_reasons=[],
    )
    return {"status": VacancyStatus.REVIEW_REQUIRED.value}


@router.post("/rescan-filtered", summary="Пересмотреть отклонённые")
async def rescan_filtered(resume_id: int, session: Session) -> dict[str, int]:
    """Прогнать отклонённые заново по текущим правилам (§10).

    Браузер не нужен: описания уже в базе. Вакансии просто возвращаются
    в очередь на анализ, статус сбрасывается.
    """
    await crud.get_or_404(session, Resume, resume_id, "Резюме")
    rows = list(
        (
            await session.scalars(
                select(ResumeVacancy).where(
                    ResumeVacancy.resume_id == resume_id,
                    ResumeVacancy.status.in_(
                        [VacancyStatus.FILTERED_OUT.value, VacancyStatus.REJECTED_BY_AI.value]
                    ),
                )
            )
        ).all()
    )
    for row in rows:
        row.status = VacancyStatus.DISCOVERED.value
        row.skip_reason = None
        row.skip_details = None
        row.decided_at = None
    await session.commit()
    return {"reset": len(rows)}


@router.post("/{vacancy_id}/recheck-suspicious", summary="Перепроверить жёсткие правила скама")
async def recheck_suspicious(vacancy_id: int, resume_id: int, session: Session) -> dict[str, Any]:
    vacancy = await crud.get_or_404(session, Vacancy, vacancy_id, "Вакансия")
    reasons = check_suspicious(
        title=vacancy.title,
        description=vacancy.description,
        company_name=vacancy.company_name,
    )
    await repo.ensure_decision(
        session,
        resume_id,
        vacancy_id,
        is_suspicious=bool(reasons),
        suspicious_reasons=reasons,
    )
    return {"is_suspicious": bool(reasons), "reasons": reasons}


class LetterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    source: str
    language: str
    content: str
    char_count: int
    fact_check_json: dict[str, Any] | None
    fact_check_passed: bool | None
    is_selected: bool
    created_at: datetime


@router.get("/{vacancy_id}/letters", response_model=list[LetterOut], summary="Версии писем")
async def list_letters(vacancy_id: int, resume_id: int, session: Session) -> list[Letter]:
    decision = await repo.get_decision(session, resume_id, vacancy_id)
    if decision is None:
        return []
    return list(
        (
            await session.scalars(
                select(Letter)
                .where(Letter.resume_vacancy_id == decision.id)
                .order_by(Letter.version.desc())
            )
        ).all()
    )
