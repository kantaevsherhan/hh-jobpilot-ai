"""Промпты: дефолты из файлов, хранение в БД, подстановка переменных."""

import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PROMPT_KEY_LABELS, PromptKey
from app.storage.models import Prompt

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def default_text(key: str) -> str:
    path = PROMPTS_DIR / f"{key}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


async def seed_defaults(session: AsyncSession) -> int:
    """Залить дефолтные промпты в базу. Существующие не трогаются:
    пользователь мог их поправить, и перезапуск не должен это стирать."""
    existing = {p.key for p in (await session.scalars(select(Prompt))).all()}
    added = 0
    for key in PromptKey:
        if key.value in existing:
            continue
        session.add(
            Prompt(
                key=key.value,
                title=PROMPT_KEY_LABELS[key],
                content=default_text(key.value),
            )
        )
        added += 1
    if added:
        await session.commit()
    return added


async def get_text(session: AsyncSession, key: str) -> str:
    prompt = await session.scalar(select(Prompt).where(Prompt.key == key))
    return prompt.content if prompt else default_text(key)


def render(template: str, variables: dict[str, Any]) -> str:
    """Подставить {{переменные}}. Незаполненные заменяются на прочерк,
    чтобы модель не получала литерал «{{allowed_facts}}» в промпте."""

    def replace(match: re.Match[str]) -> str:
        value = variables.get(match.group(1))
        if value is None or value == "" or value == []:
            return "—"
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value)
        return str(value)

    return _PLACEHOLDER.sub(replace, template)
