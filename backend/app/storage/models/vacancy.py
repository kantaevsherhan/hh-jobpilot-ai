"""Вакансии, решения по ним, письма и отклики (§6, §10, §21)."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import LetterSource, VacancyStatus
from app.storage.models.base import Base, TimestampMixin, utcnow


class Vacancy(Base):
    """Только факты с HH. Решений тут нет — они в resume_vacancies."""

    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    hh_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))

    company_hh_id: Mapped[str | None] = mapped_column(String(50))
    company_name: Mapped[str | None] = mapped_column(String(300), index=True)

    description: Mapped[str] = mapped_column(Text, default="")
    description_lang: Mapped[str | None] = mapped_column(String(5))

    salary_from: Mapped[int | None] = mapped_column(Integer)
    salary_to: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(10))
    salary_gross: Mapped[bool | None] = mapped_column(Boolean)

    work_format: Mapped[str | None] = mapped_column(String(30))
    experience: Mapped[str | None] = mapped_column(String(50))
    employment: Mapped[str | None] = mapped_column(String(50))
    schedule: Mapped[str | None] = mapped_column(String(50))
    area: Mapped[str | None] = mapped_column(String(100))

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    seen_count: Mapped[int] = mapped_column(Integer, default=1)

    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Сырой объект со страницы: пригодится, когда понадобится поле,
    # о котором сейчас не подумали (§10)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column()


class ResumeVacancy(Base, TimestampMixin):
    """Решение конкретного резюме по конкретной вакансии."""

    __tablename__ = "resume_vacancies"
    __table_args__ = (
        UniqueConstraint("resume_id", "vacancy_id", name="uq_resume_vacancy"),
        Index("ix_resume_vacancies_resume_status", "resume_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))

    status: Mapped[str] = mapped_column(String(40), default=VacancyStatus.DISCOVERED.value)
    skip_reason: Mapped[str | None] = mapped_column(String(40))
    skip_details: Mapped[str | None] = mapped_column(Text)

    score: Mapped[int | None] = mapped_column(Integer)
    analysis_json: Mapped[dict[str, Any] | None] = mapped_column()

    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    suspicious_reasons: Mapped[list[Any]] = mapped_column(default=list)
    hidden_instructions: Mapped[list[Any]] = mapped_column(default=list)

    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vacancy: Mapped[Vacancy] = relationship(lazy="joined")
    letters: Mapped[list["Letter"]] = relationship(
        back_populates="resume_vacancy", cascade="all, delete-orphan"
    )


class Letter(Base):
    """Версия сопроводительного письма. Все версии сохраняются (§17)."""

    __tablename__ = "letters"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("resume_vacancies.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(20), default=LetterSource.AI.value)
    language: Mapped[str] = mapped_column(String(5), default="ru")

    content: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    fact_check_json: Mapped[dict[str, Any] | None] = mapped_column()
    fact_check_passed: Mapped[bool | None] = mapped_column(Boolean)

    provider_used: Mapped[str | None] = mapped_column(String(100))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)

    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resume_vacancy: Mapped[ResumeVacancy] = relationship(back_populates="letters")


class Application(Base):
    """Отклик. vacancy_id уникален — это и есть защита от повторного отклика (§21)."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"), unique=True, index=True
    )
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    letter_id: Mapped[int | None] = mapped_column(ForeignKey("letters.id", ondelete="SET NULL"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))

    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    hh_status: Mapped[str | None] = mapped_column(String(20))
    hh_status_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    answers_json: Mapped[dict[str, Any] | None] = mapped_column()
    error_code: Mapped[str | None] = mapped_column(String(50))
    screenshot_path: Mapped[str | None] = mapped_column(String(500))

    vacancy: Mapped[Vacancy] = relationship(lazy="joined")
