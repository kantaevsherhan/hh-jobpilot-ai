"""Сборка всех hard-фильтров в один проход (§11).

Фильтры остаются чистыми функциями: движок получает уже готовые правила
и данные вакансии, в базу не ходит.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.core.enums import SkipReason
from app.filters import age, company, experience, keywords, salary, work_format
from app.filters.base import FilterResult
from app.filters.company import CompanyRuleSpec, CompanyVerdict


@dataclass(frozen=True, slots=True)
class VacancyFacts:
    """Что известно о вакансии на момент проверки.

    До открытия карточки описание пустое — часть проверок просто пропускается,
    и это нормально: отсев по заголовку экономит открытие карточки.
    """

    title: str
    description: str = ""
    company_name: str | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    currency: str | None = None
    salary_gross: bool | None = None
    work_format: str | None = None
    experience: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProfileRules:
    """Условия поискового профиля плюс общие настройки."""

    min_salary: int | None = None
    currency: str = "KZT"
    allow_unknown_salary: bool = True
    remote_mode: str = "ANY"
    experience_levels: list[str] = field(default_factory=list)
    max_age_days: int | None = None
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    currency_rates: dict[str, float] = field(default_factory=dict)
    tax_rate: float = 0.10


@dataclass(frozen=True, slots=True)
class EngineResult:
    passed: bool
    reason: SkipReason | None = None
    details: str | None = None
    notes: list[str] = field(default_factory=list)
    score_delta: int = 0
    force_review: bool = False


def run_filters(
    facts: VacancyFacts,
    rules: ProfileRules,
    company_rules: list[CompanyRuleSpec] | None = None,
    *,
    now: datetime | None = None,
) -> EngineResult:
    verdict: CompanyVerdict = company.check_company(facts.company_name, company_rules or [])
    checks: list[FilterResult] = [
        verdict.result,
        keywords.check_keywords(
            title=facts.title,
            description=facts.description,
            include=rules.include_keywords if facts.description else None,
            exclude=rules.exclude_keywords,
        ),
        salary.check_salary(
            salary_from=facts.salary_from,
            salary_to=facts.salary_to,
            currency=facts.currency,
            salary_gross=facts.salary_gross,
            rules=salary.SalaryRules(
                min_salary=rules.min_salary,
                currency=rules.currency,
                allow_unknown_salary=rules.allow_unknown_salary,
                rates=rules.currency_rates,
                tax_rate=rules.tax_rate,
            ),
        ),
        work_format.check_work_format(facts.work_format, rules.remote_mode),
        experience.check_experience(facts.experience, rules.experience_levels),
        age.check_age(facts.published_at, rules.max_age_days, now=now),
    ]

    notes = [check.note for check in checks if check.note]

    for check in checks:
        if not check.passed:
            return EngineResult(
                passed=False,
                reason=check.reason,
                details=check.details,
                notes=[note for note in notes if note],
            )

    return EngineResult(
        passed=True,
        notes=[note for note in notes if note],
        score_delta=verdict.score_delta,
        force_review=verdict.force_review,
    )
