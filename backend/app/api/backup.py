"""Резервные копии и выгрузки (§29)."""

import csv
import io
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import Session
from app.core.enums import VACANCY_STATUS_LABELS
from app.storage.backup import create_backup
from app.storage.models import Application, ResumeVacancy, Vacancy

router = APIRouter(tags=["Резервные копии"])


@router.post("/backup", summary="Резервная копия базы")
async def backup() -> dict[str, Any]:
    return create_backup()


def _csv_response(rows: list[list[Any]], header: list[str], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    # BOM, иначе Excel открывает кириллицу кракозябрами
    content = "﻿" + buffer.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/vacancies.csv", summary="Выгрузить вакансии")
async def export_vacancies(session: Session, resume_id: int) -> StreamingResponse:
    result = await session.execute(
        select(Vacancy, ResumeVacancy)
        .join(ResumeVacancy, ResumeVacancy.vacancy_id == Vacancy.id)
        .where(ResumeVacancy.resume_id == resume_id)
        .order_by(Vacancy.id)
    )
    rows = [
        [
            vacancy.hh_id,
            vacancy.title,
            vacancy.company_name or "",
            vacancy.salary_from or "",
            vacancy.salary_to or "",
            vacancy.currency or "",
            VACANCY_STATUS_LABELS.get(decision.status, decision.status),
            decision.score if decision.score is not None else "",
            decision.skip_details or "",
            vacancy.url,
        ]
        for vacancy, decision in result.all()
    ]
    return _csv_response(
        rows,
        [
            "hh_id",
            "Вакансия",
            "Компания",
            "Зарплата от",
            "Зарплата до",
            "Валюта",
            "Статус",
            "Оценка",
            "Причина",
            "Ссылка",
        ],
        "vacancies.csv",
    )


@router.get("/export/applications.csv", summary="Выгрузить отклики")
async def export_applications(session: Session, resume_id: int) -> StreamingResponse:
    result = await session.execute(
        select(Application, Vacancy)
        .join(Vacancy, Vacancy.id == Application.vacancy_id)
        .where(Application.resume_id == resume_id)
        .order_by(Application.applied_at)
    )
    rows = [
        [
            application.applied_at.strftime("%Y-%m-%d %H:%M"),
            vacancy.title,
            vacancy.company_name or "",
            application.hh_status or "",
            application.error_code or "",
            vacancy.url,
        ]
        for application, vacancy in result.all()
    ]
    return _csv_response(
        rows,
        ["Дата", "Вакансия", "Компания", "Статус на HH", "Ошибка", "Ссылка"],
        "applications.csv",
    )
