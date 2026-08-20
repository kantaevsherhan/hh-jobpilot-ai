"""Команды обслуживания: make seed, make backup.

Нужны для случаев, когда бэкенд не поднят или база создаётся с нуля.
"""

import asyncio
import sys

from app.core.logging import setup_logging
from app.llm.prompts import seed_default_provider, seed_defaults
from app.storage import session as db
from app.storage.backup import create_backup


async def seed() -> None:
    async with db.session_factory()() as session:
        prompts = await seed_defaults(session)
        provider = await seed_default_provider(session)
    print(f"Промптов добавлено: {prompts}")
    print("Провайдер по умолчанию: " + ("заведён" if provider else "уже был"))


def backup() -> None:
    result = create_backup()
    print(f"Копия: {result['path']} ({int(result['size_bytes']) // 1024} КБ)")


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
