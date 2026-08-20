"""Резервное копирование базы (§29).

Одна реализация на CLI и HTTP: раньше они собирали путь и копировали файл
независимо, и вели себя по-разному.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger(__name__)


def create_backup(target_dir: Path | None = None) -> dict[str, Any]:
    """Сделать копию базы и проверить её целостность.

    Копируем через штатный Online Backup API SQLite, а не копированием
    файла: приложение может писать в базу прямо сейчас, и при обычном
    копировании часть данных осталась бы в WAL-журнале, а копия — битой.
    """
    source = settings.database_path
    if source is None:
        raise AppError(
            "BACKUP_UNSUPPORTED",
            "Копия делается только для SQLite",
            recoverable=False,
        )
    if not source.exists():
        raise AppError(
            "BACKUP_UNSUPPORTED",
            f"Файл базы не найден: {source}",
            recoverable=False,
        )

    directory = target_dir or settings.backups_dir
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"jobpilot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"

    with sqlite3.connect(source) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)

    with sqlite3.connect(target) as check:
        result = check.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        target.unlink(missing_ok=True)
        raise AppError(
            "BACKUP_CORRUPTED",
            "Копия получилась повреждённой и была удалена",
            technical_details=str(result),
            recoverable=True,
        )

    log.info("Резервная копия: %s", target)
    return {"path": str(target), "size_bytes": target.stat().st_size}
