"""Статистика: воронка, технологии, зарплаты (§28)."""

import statistics
from collections import Counter
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import Session
from app.core.enums import HHApplicationStatus, VacancyStatus
from app.storage.models import Application, Resume, ResumeVacancy, Vacancy

router = APIRouter(prefix="/stats", tags=["Статистика"])

SUITABLE = (
    VacancyStatus.REVIEW_REQUIRED.value,
    VacancyStatus.RECOMMENDED.value,
    VacancyStatus.LETTER_READY.value,
    VacancyStatus.APPLY_PREPARED.value,
    VacancyStatus.APPLIED.value,
)


async def _count(session: Session, resume_id: int, *conditions: Any) -> int:
    query = (
        select(func.count())
        .select_from(ResumeVacancy)
        .where(ResumeVacancy.resume_id == resume_id, *conditions)
    )
    return (await session.scalar(query)) or 0


@router.get("/overview", summary="Карточки дашборда")
async def overview(session: Session, resume_id: int) -> dict[str, int]:
    applied = (
        await session.scalar(
            select(func.count()).select_from(Application).where(Application.resume_id == resume_id)
        )
    ) or 0
    return {
        "found": await _count(session, resume_id),
        "suitable": await _count(session, resume_id, ResumeVacancy.status.in_(SUITABLE)),
        "applied": applied,
        "rejected": await _count(
            session,
            resume_id,
            ResumeVacancy.status.in_(
                [VacancyStatus.FILTERED_OUT.value, VacancyStatus.REJECTED_BY_AI.value]
            ),
        ),
        "suspicious": await _count(session, resume_id, ResumeVacancy.is_suspicious),
        "review": await _count(
            session,
            resume_id,
            ResumeVacancy.status.in_(
                [VacancyStatus.REVIEW_REQUIRED.value, VacancyStatus.RECOMMENDED.value]
            ),
        ),
        "errors": await _count(
            session,
            resume_id,
            ResumeVacancy.status.in_(
                [VacancyStatus.ANALYSIS_FAILED.value, VacancyStatus.PARSE_FAILED.value]
            ),
        ),
    }


@router.get("/funnel", summary="Воронка")
async def funnel(session: Session, resume_id: int) -> list[dict[str, Any]]:
    found = await _count(session, resume_id)
    filtered_out = await _count(
        session, resume_id, ResumeVacancy.status == VacancyStatus.FILTERED_OUT.value
    )
    suitable = await _count(session, resume_id, ResumeVacancy.status.in_(SUITABLE))

    applications = list(
        (await session.scalars(select(Application).where(Application.resume_id == resume_id))).all()
    )
    viewed = sum(
        1
        for a in applications
        if a.hh_status
        in (
            HHApplicationStatus.VIEWED.value,
            HHApplicationStatus.INVITED.value,
            HHApplicationStatus.DECLINED.value,
        )
    )
    invited = sum(1 for a in applications if a.hh_status == HHApplicationStatus.INVITED.value)

    return [
        {"stage": "Найдено", "value": found},
        {"stage": "Прошло фильтры", "value": found - filtered_out},
        {"stage": "Подходящих", "value": suitable},
        {"stage": "Откликов", "value": len(applications)},
        {"stage": "Просмотрено", "value": viewed},
        {"stage": "Приглашений", "value": invited},
    ]


@router.get("/technologies", summary="Требования рынка против навыков резюме")
async def technologies(session: Session, resume_id: int, limit: int = 25) -> dict[str, Any]:
    resume = await session.get(Resume, resume_id)
    own = {skill.name.lower() for skill in resume.skills} if resume else set()

    rows = list(
        (
            await session.scalars(
                select(ResumeVacancy).where(
                    ResumeVacancy.resume_id == resume_id, ResumeVacancy.analysis_json.is_not(None)
                )
            )
        ).all()
    )

    counter: Counter[str] = Counter()
    for row in rows:
        parsed = (row.analysis_json or {}).get("parsed", {})
        for skill in [*parsed.get("required_skills", []), *parsed.get("preferred_skills", [])]:
            counter[str(skill).strip()] += 1

    top: list[dict[str, Any]] = [
        {"name": name, "count": count} for name, count in counter.most_common(limit)
    ]
    # Самое полезное: чего рынок хочет, а в резюме этого нет
    gaps = [item for item in top if str(item["name"]).lower() not in own]

    return {"top": top, "missing_in_resume": gaps, "analyzed_vacancies": len(rows)}


@router.get("/salaries", summary="Зарплаты по прошедшим фильтр")
async def salaries(session: Session, resume_id: int) -> dict[str, Any]:
    rows = await session.execute(
        select(Vacancy.salary_from, Vacancy.currency)
        .join(ResumeVacancy, ResumeVacancy.vacancy_id == Vacancy.id)
        .where(
            ResumeVacancy.resume_id == resume_id,
            ResumeVacancy.status.in_(SUITABLE),
            Vacancy.salary_from.is_not(None),
        )
    )
    values = [value for value, currency in rows.all() if value and currency in (None, "KZT")]

    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None, "median": None}

    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": round(statistics.mean(values)),
        "median": round(statistics.median(values)),
    }
