"""Фильтр свежести вакансии (§11)."""

from datetime import UTC, datetime

from app.core.enums import SkipReason
from app.filters.base import FilterResult


def check_age(
    published_at: datetime | None,
    max_age_days: int | None,
    *,
    now: datetime | None = None,
) -> FilterResult:
    if not max_age_days or published_at is None:
        return FilterResult.ok()

    moment = now or datetime.now(UTC)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    age_days = (moment - published).days

    if age_days > max_age_days:
        return FilterResult.fail(
            SkipReason.TOO_OLD,
            f"Опубликована {age_days} дней назад при пороге {max_age_days}",
        )
    return FilterResult.ok()
