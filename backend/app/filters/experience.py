"""Фильтр опыта по диапазонам HH (§11)."""

from app.core.enums import SkipReason
from app.filters.base import FilterResult

# Как HH называет диапазоны словами в разных местах интерфейса
TEXT_TO_CODE = {
    "нет опыта": "noExperience",
    "не требуется": "noExperience",
    "от 1 года до 3 лет": "between1And3",
    "1–3": "between1And3",
    "от 3 до 6 лет": "between3And6",
    "3–6": "between3And6",
    "более 6 лет": "moreThan6",
}


def to_code(experience: str | None) -> str | None:
    if not experience:
        return None
    lowered = experience.lower().strip()
    if lowered in {"noexperience", "between1and3", "between3and6", "morethan6"}:
        return {
            "noexperience": "noExperience",
            "between1and3": "between1And3",
            "between3and6": "between3And6",
            "morethan6": "moreThan6",
        }[lowered]
    for text, code in TEXT_TO_CODE.items():
        if text in lowered:
            return code
    return None


def check_experience(experience: str | None, allowed_levels: list[str] | None) -> FilterResult:
    if not allowed_levels:
        return FilterResult.ok()

    code = to_code(experience)
    # Не распознали — не отсекаем: лучше лишняя вакансия, чем потерянная
    if code is None:
        return FilterResult.ok("Требуемый опыт не распознан")

    if code not in allowed_levels:
        return FilterResult.fail(SkipReason.EXPERIENCE, f"Требуемый опыт: {experience}")
    return FilterResult.ok()
