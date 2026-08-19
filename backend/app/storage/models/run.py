"""Прогоны, очередь задач и события (§22)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import BotMode, JobState, RunStatus, RuntimeMode
from app.storage.models.base import Base, utcnow


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    search_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="SET NULL")
    )

    mode: Mapped[str] = mapped_column(String(20), default=BotMode.MANUAL.value)
    runtime_mode: Mapped[str] = mapped_column(String(20), default=RuntimeMode.DRY_RUN.value)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.RUNNING.value, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stop_reason: Mapped[str | None] = mapped_column(String(40))

    counters_json: Mapped[dict[str, Any]] = mapped_column(default=dict)
    last_error_code: Mapped[str | None] = mapped_column(String(50))
    last_error_step: Mapped[str | None] = mapped_column(String(50))


class Job(Base):
    """Задача очереди. Живёт в БД, а не в памяти: прогон обязан переживать
    паузу, остановку и падение приложения (§22)."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_run_state", "run_id", "state"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(30))
    payload_json: Mapped[dict[str, Any]] = mapped_column(default=dict)
    state: Mapped[str] = mapped_column(String(20), default=JobState.PENDING.value)

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (Index("ix_run_events_run_id_id", "run_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    resume_vacancy_id: Mapped[int | None] = mapped_column(
        ForeignKey("resume_vacancies.id", ondelete="SET NULL")
    )
    level: Mapped[str] = mapped_column(String(10), default="info")
    type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
