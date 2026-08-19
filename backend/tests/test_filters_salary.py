"""Фильтр зарплаты: валюты, gross/net, неизвестная зарплата (§11, §30)."""

from app.core.enums import SkipReason
from app.filters.salary import SalaryRules, check_salary

RATES = {"KZT": 1.0, "RUB": 5.7, "USD": 500.0, "EUR": 540.0}


def check(**kwargs: object):
    defaults = {
        "salary_from": None,
        "salary_to": None,
        "currency": "KZT",
        "salary_gross": False,
        "rules": SalaryRules(min_salary=500_000, currency="KZT", rates=RATES),
    }
    return check_salary(**{**defaults, **kwargs})  # type: ignore[arg-type]


def test_зарплата_ниже_минимума_отсекается() -> None:
    result = check(salary_from=300_000)

    assert result.passed is False
    assert result.reason == SkipReason.SALARY_TOO_LOW


def test_зарплата_выше_минимума_проходит() -> None:
    assert check(salary_from=700_000).passed is True


def test_при_отсутствии_нижней_границы_сравнивается_верхняя() -> None:
    assert check(salary_to=300_000).passed is False
    assert check(salary_to=800_000).passed is True


def test_доллары_переводятся_в_тенге() -> None:
    # 1500 USD = 750 000 KZT при курсе 500 — выше минимума 500 000
    assert check(salary_from=1500, currency="USD").passed is True
    assert check(salary_from=800, currency="USD").passed is False


def test_рубли_приходят_кодом_rur() -> None:
    # HH отдаёт рубли как RUR: 100 000 RUR = 570 000 KZT
    assert check(salary_from=100_000, currency="RUR").passed is True


def test_gross_уменьшается_на_налог() -> None:
    # 540 000 gross при ставке 10% дают 486 000 на руки — ниже минимума
    assert check(salary_from=540_000, salary_gross=True).passed is False
    assert check(salary_from=540_000, salary_gross=False).passed is True


def test_неизвестный_курс_не_отсекает_вакансию() -> None:
    result = check(salary_from=1000, currency="GBP")

    assert result.passed is True
    assert result.note is not None


def test_зарплата_не_указана_и_разрешена() -> None:
    rules = SalaryRules(min_salary=500_000, allow_unknown_salary=True, rates=RATES)

    assert check(rules=rules).passed is True


def test_зарплата_не_указана_и_запрещена() -> None:
    rules = SalaryRules(min_salary=500_000, allow_unknown_salary=False, rates=RATES)

    result = check(rules=rules)

    assert result.passed is False
    assert result.reason == SkipReason.SALARY_UNKNOWN


def test_без_минимума_фильтр_ничего_не_отсекает() -> None:
    assert check(salary_from=1, rules=SalaryRules(rates=RATES)).passed is True
