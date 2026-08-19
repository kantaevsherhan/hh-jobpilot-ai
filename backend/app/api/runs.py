"""Прогоны и лента событий (§26, §27)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import Session
from app.pipeline import events
from app.storage.models import Run
from app.storage.repositories import crud

router = APIRouter(prefix="/runs", tags=["Прогоны"])


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    mode: str
    runtime_mode: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    stop_reason: str | None
    counters_json: dict[str, Any]
    last_error_code: str | None
    last_error_step: str | None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    type: str
    message: str
    payload_json: dict[str, Any] | None
    created_at: datetime


@router.get("", response_model=list[RunOut], summary="Список прогонов")
async def list_runs(session: Session, resume_id: int | None = None, limit: int = 30) -> list[Run]:
    query = select(Run).order_by(Run.id.desc()).limit(limit)
    if resume_id is not None:
        query = query.where(Run.resume_id == resume_id)
    return list((await session.scalars(query)).all())


@router.get("/{run_id}", response_model=RunOut, summary="Прогон по id")
async def get_run(run_id: int, session: Session) -> Run:
    return await crud.get_or_404(session, Run, run_id, "Прогон")


@router.get("/{run_id}/events", response_model=list[EventOut], summary="Лента событий")
async def run_events(run_id: int, session: Session, after: int = 0, limit: int = 200) -> list[Any]:
    """Инкрементально: фронт дописывает хвост, а не перезагружает всё (§27)."""
    return await events.read_after(session, run_id, after, limit)
