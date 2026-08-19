"""Фильтр формата работы (§11)."""

from app.core.enums import RemoteMode, SkipReason, WorkFormat
from app.filters.base import FilterResult

ALLOWED: dict[str, set[str]] = {
    RemoteMode.REMOTE_ONLY: {WorkFormat.REMOTE},
    RemoteMode.REMOTE_OR_HYBRID: {WorkFormat.REMOTE, WorkFormat.HYBRID},
}

LABELS: dict[str, str] = {
    WorkFormat.REMOTE: "удалённо",
    WorkFormat.HYBRID: "гибрид",
    WorkFormat.OFFICE: "офис",
    WorkFormat.UNKNOWN: "не указан",
}


def check_work_format(work_format: str | None, remote_mode: str) -> FilterResult:
    if remote_mode == RemoteMode.ANY:
        return FilterResult.ok()

    allowed = ALLOWED.get(remote_mode, set())
    value = work_format or WorkFormat.UNKNOWN

    # Неизвестный формат не отсекаем: он выяснится при чтении описания,
    # а терять вакансию из-за пустого поля на HH — дорого
    if value == WorkFormat.UNKNOWN:
        return FilterResult.ok("Формат работы не указан")

    if value not in allowed:
        return FilterResult.fail(
            SkipReason.WORK_FORMAT,
            f"Формат «{LABELS.get(value, value)}» не подходит",
        )
    return FilterResult.ok()
