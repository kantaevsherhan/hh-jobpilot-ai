"""Стоп-слова и обязательные слова (§11).

Проверка регистронезависимая, по заголовку и описанию. Стоп-слова
применяются к заголовку ещё на этапе выдачи, до открытия карточки.
"""

from app.core.enums import SkipReason
from app.filters.base import FilterResult


def check_keywords(
    *,
    title: str,
    description: str = "",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> FilterResult:
    haystack = f"{title}\n{description}".lower()

    for word in exclude or []:
        if word.strip() and word.strip().lower() in haystack:
            return FilterResult.fail(SkipReason.KEYWORD_STOP, f"Стоп-слово «{word.strip()}»")

    required = [word.strip() for word in include or [] if word.strip()]
    if required and not any(word.lower() in haystack for word in required):
        return FilterResult.fail(
            SkipReason.KEYWORD_MISSING,
            f"Нет ни одного из обязательных слов: {', '.join(required)}",
        )

    return FilterResult.ok()
