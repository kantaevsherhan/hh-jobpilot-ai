"""Фильтр зарплаты: валюты, gross/net, неизвестная зарплата (§11)."""

from dataclasses import dataclass

from app.core.enums import SkipReason
from app.filters.base import FilterResult

# HH отдаёт рубли кодом RUR, а не RUB
CURRENCY_ALIASES = {"RUR": "RUB", "KZT": "KZT", "USD": "USD", "EUR": "EUR", "RUB": "RUB"}


@dataclass(frozen=True, slots=True)
class SalaryRules:
    min_salary: int | None = None
    currency: str = "KZT"
    allow_unknown_salary: bool = True
    rates: dict[str, float] | None = None
    tax_rate: float = 0.10


def normalize_currency(code: str | None) -> str | None:
    return CURRENCY_ALIASES.get((code or "").upper()) if code else None


def convert(amount: int, currency: str, target: str, rates: dict[str, float]) -> float | None:
    """Перевести в валюту профиля. Курса нет → None, вакансия не отсекается."""
    if currency == target:
        return float(amount)
    source_rate, target_rate = rates.get(currency), rates.get(target)
    if not source_rate or not target_rate:
        return None
    return amount * source_rate / target_rate


def check_salary(
    *,
    salary_from: int | None,
    salary_to: int | None,
    currency: str | None,
    salary_gross: bool | None,
    rules: SalaryRules,
) -> FilterResult:
    if rules.min_salary is None:
        return FilterResult.ok()

    # Сравниваем по нижней границе; указана только верхняя — сравниваем её
    amount = salary_from if salary_from else salary_to
    if not amount:
        if rules.allow_unknown_salary:
            return FilterResult.ok("Зарплата не указана, пропущена по настройке профиля")
        return FilterResult.fail(SkipReason.SALARY_UNKNOWN, "Зарплата не указана")

    target = normalize_currency(rules.currency) or "KZT"
    rates = rules.rates or {}

    if currency:
        code = normalize_currency(currency)
        if code is None:
            # Валюта не опознана — считать её валютой профиля нельзя:
            # так 1000 фунтов превратились бы в 1000 тенге и вакансия отсеклась
            return FilterResult.ok(f"Валюта {currency} не опознана, зарплата не сравнивалась")
    else:
        code = target

    converted = convert(amount, code, target, rates)
    if converted is None:
        # Курса нет — отсекать по нему нельзя, иначе тихо потеряем вакансии
        return FilterResult.ok(f"Курс {code} не задан, зарплата не сравнивалась")

    if salary_gross:
        converted *= 1 - rules.tax_rate

    if converted < rules.min_salary:
        return FilterResult.fail(
            SkipReason.SALARY_TOO_LOW,
            f"{round(converted):,} {target} против минимума {rules.min_salary:,} {target}".replace(
                ",", " "
            ),
        )
    return FilterResult.ok()
