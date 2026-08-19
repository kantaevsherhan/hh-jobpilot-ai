"""Все модели. Импорт здесь нужен Alembic для autogenerate."""

from app.storage.models.base import Base
from app.storage.models.config import CompanyRule, LLMProvider, Prompt, Setting
from app.storage.models.resume import (
    LetterExample,
    Resume,
    ResumeSkill,
    SearchProfile,
    SearchQuery,
)
from app.storage.models.run import Job, Run, RunEvent
from app.storage.models.vacancy import Application, Letter, ResumeVacancy, Vacancy

__all__ = [
    "Application",
    "Base",
    "CompanyRule",
    "Job",
    "LLMProvider",
    "Letter",
    "LetterExample",
    "Prompt",
    "Resume",
    "ResumeSkill",
    "ResumeVacancy",
    "Run",
    "RunEvent",
    "SearchProfile",
    "SearchQuery",
    "Setting",
    "Vacancy",
]
