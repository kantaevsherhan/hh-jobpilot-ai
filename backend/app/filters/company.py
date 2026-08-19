"""Правила по компаниям (§12)."""

from dataclasses import dataclass

from app.core.enums import CompanyRuleAction, MatchType, SkipReason
from app.filters.base import FilterResult


@dataclass(frozen=True, slots=True)
class CompanyRuleSpec:
    """Правило в виде, не зависящем от модели БД — чтобы фильтр остался чистым."""

    match_type: str
    value: str
    action: str
    case_sensitive: bool = False
    score_delta: int = 0
    note: str | None = None


def matches(rule: CompanyRuleSpec, company_name: str | None) -> bool:
    """CONTAINS «vash» ловит «Vash Group», «VASH COMPANY» и «ТОО Vash»."""
    if not company_name or not rule.value:
        return False

    name = company_name if rule.case_sensitive else company_name.lower()
    value = rule.value if rule.case_sensitive else rule.value.lower()

    if rule.match_type == MatchType.EQUALS:
        return name.strip() == value.strip()
    return value in name


@dataclass(frozen=True, slots=True)
class CompanyVerdict:
    result: FilterResult
    score_delta: int = 0
    force_review: bool = False
    matched_rule: CompanyRuleSpec | None = None


def check_company(company_name: str | None, rules: list[CompanyRuleSpec]) -> CompanyVerdict:
    """Первое совпавшее правило SKIP решает исход. Бонусы и штрафы
    суммируются и применяются к скору позже (§12)."""
    score_delta = 0
    force_review = False
    matched: CompanyRuleSpec | None = None

    for rule in rules:
        if not matches(rule, company_name):
            continue
        matched = matched or rule

        if rule.action == CompanyRuleAction.SKIP:
            return CompanyVerdict(
                result=FilterResult.fail(
                    SkipReason.COMPANY_RULE,
                    rule.note or f"Правило по компании: «{rule.value}»",
                ),
                matched_rule=rule,
            )
        if rule.action == CompanyRuleAction.ALWAYS_REVIEW:
            force_review = True
        elif rule.action in (CompanyRuleAction.BOOST, CompanyRuleAction.PENALTY):
            score_delta += rule.score_delta

    return CompanyVerdict(
        result=FilterResult.ok(),
        score_delta=score_delta,
        force_review=force_review,
        matched_rule=matched,
    )
