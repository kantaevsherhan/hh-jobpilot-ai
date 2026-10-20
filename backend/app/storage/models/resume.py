"""Резюме и всё, что принадлежит ему напрямую (§7, §8, §17)."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RemoteMode
from app.storage.models.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    """Источник истины о кандидате. Текст резюме вставляется с HH как есть."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    hh_resume_url: Mapped[str | None] = mapped_column(String(500))
    hh_resume_id: Mapped[str | None] = mapped_column(String(100))

    raw_text: Mapped[str] = mapped_column(Text, default="")
    digest_json: Mapped[dict[str, Any] | None] = mapped_column()
    digest_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allowed_facts: Mapped[str] = mapped_column(Text, default="")
    letter_languages: Mapped[list[Any]] = mapped_column(default=lambda: ["ru"])

    # Пороги решения (§15). Хранятся на резюме: для разных профессий они разные
    min_score: Mapped[int] = mapped_column(Integer, default=75)
    auto_apply_score: Mapped[int] = mapped_column(Integer, default=90)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    # Первый прогон нового резюме принудительно идёт в DRY_RUN (§20)
    has_completed_run: Mapped[bool] = mapped_column(Boolean, default=False)

    skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", lazy="selectin"
    )


class ResumeSkill(Base):
    """Навык из выжимки. Нужен hard-фильтрам и статистике, не модели."""

    __tablename__ = "resume_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)

    resume: Mapped[Resume] = relationship(back_populates="skills")


class LetterExample(Base, TimestampMixin):
    """Пример письма пользователя — ориентир стиля для модели (§17)."""

    __tablename__ = "letter_examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), default="Общий")
    tone: Mapped[str] = mapped_column(String(50), default="Нейтральный")
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)


class SearchProfile(Base, TimestampMixin):
    """Набор поисковых условий внутри резюме (§8)."""

    __tablename__ = "search_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)

    remote_mode: Mapped[str] = mapped_column(String(30), default=RemoteMode.ANY.value)
    allowed_work_formats: Mapped[list[Any]] = mapped_column(default=list)

    min_salary: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="KZT")
    allow_unknown_salary: Mapped[bool] = mapped_column(Boolean, default=True)

    experience_levels: Mapped[list[Any]] = mapped_column(default=list)
    areas: Mapped[list[Any]] = mapped_column(default=list)
    max_age_days: Mapped[int | None] = mapped_column(Integer, default=7)

    include_keywords: Mapped[list[Any]] = mapped_column(default=list)
    exclude_keywords: Mapped[list[Any]] = mapped_column(default=list)
    max_vacancies_per_run: Mapped[int] = mapped_column(Integer, default=25)
    # Лента «Для вас» на HH — подбор вакансий под резюме. Её хватает и без запросов
    use_recommendations: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )

    queries: Mapped[list["SearchQuery"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )


class SearchQuery(Base):
    """Одна поисковая строка профиля. Три запроса дают одну вакансию один раз (§10)."""

    __tablename__ = "search_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_profile_id: Mapped[int] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(300))

    profile: Mapped[SearchProfile] = relationship(back_populates="queries")
