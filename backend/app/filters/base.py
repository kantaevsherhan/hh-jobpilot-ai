"""Общие типы фильтров.

Фильтры — чистые функции: принимают данные, возвращают результат.
В базу они не ходят и ничего не сохраняют (§4).
"""

from dataclasses import dataclass

from app.core.enums import SkipReason


@dataclass(frozen=True, slots=True)
class FilterResult:
    passed: bool
    reason: SkipReason | None = None
    details: str | None = None
    # Пометка для случаев, когда отсечь нельзя, но знать полезно
    note: str | None = None

    @staticmethod
    def ok(note: str | None = None) -> "FilterResult":
        return FilterResult(passed=True, note=note)

    @staticmethod
    def fail(reason: SkipReason, details: str) -> "FilterResult":
        return FilterResult(passed=False, reason=reason, details=details)
