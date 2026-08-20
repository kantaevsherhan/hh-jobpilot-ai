"""Команды обслуживания: make seed, make backup.

Нужны для случаев, когда бэкенд не поднят или база создаётся с нуля.
"""

import asyncio
import shutil
import sys
from datetime import datetime

from app.core.config import ROOT_DIR, settings
from app.core.logging import setup_logging
from app.llm.prompts import seed_default_provider, seed_defaults
from app.storage import session as db


async def seed() -> None:
    async with db.session_factory()() as session:
        prompts = await seed_defaults(session)
        provider = await seed_default_provider(session)
    print(f"Промптов добавлено: {prompts}")
    print("Провайдер по умолчанию: " + ("заведён" if provider else "уже был"))


def backup() -> None:
    prefix = "sqlite+aiosqlite:///"
    source = ROOT_DIR / settings.sqlalchemy_url[len(prefix) :].lstrip("/")
    if not source.exists():
        print(f"Файл базы не найден: {source}")
        raise SystemExit(1)

    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    target = settings.backups_dir / f"jobpilot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(source, target)
    print(f"Копия: {target} ({target.stat().st_size // 1024} КБ)")


def main() -> None:
    setup_logging()
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "seed":
        asyncio.run(seed())
    elif command == "backup":
        backup()
    else:
        print("Использование: python -m app.cli {seed|backup}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
