"""Промпты: дефолты из файлов, хранение в БД, подстановка переменных."""

import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.defaults import DEFAULT_PROVIDER
from app.core.enums import PROMPT_KEY_LABELS, PromptKey
from app.storage.models import LLMProvider, Prompt, Skill

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


async def seed_default_provider(session: AsyncSession) -> bool:
    """Завести локальную Ollama, если провайдеров нет вообще.

    Без этого на свежей базе не работает ни один шаг, а руками заводить
    строку с localhost:11434 пользователю незачем — это дефолт проекта.
    """
    if await session.scalar(select(LLMProvider).limit(1)) is not None:
        return False
    session.add(LLMProvider(**DEFAULT_PROVIDER))
    await session.commit()
    return True


async def get_text(session: AsyncSession, key: str) -> str:
    prompt = await session.scalar(select(Prompt).where(Prompt.key == key))
    text = prompt.content if prompt else default_text(key)
    if key not in SKILL_TARGETS:
        return text
    rows = (await session.scalars(select(Skill).where(Skill.is_enabled).order_by(Skill.id))).all()
    return with_skills(text, [(row.name, row.content) for row in rows if key in row.prompt_keys])


# Правила подозрительности — фрагмент, который вставляется внутрь анализа, а не
# самостоятельный промпт: блок скиллов посреди списка правил сломал бы его
SKILL_TARGETS = [key.value for key in PromptKey if key != PromptKey.SUSPICIOUS_RULES]

_FRONTMATTER = re.compile(r"\A﻿?---\s*\n.*?\n---\s*(\n|\Z)", re.DOTALL)

_SKILLS_HEADER = (
    "ПОДКЛЮЧЁННЫЕ СКИЛЛЫ. Бери из них правила стиля и самопроверки. Требования к "
    "фактам и формат ответа (JSON) выше важнее скиллов. Режимы работы, команды, "
    "запуск скриптов и формат вывода, описанные в скиллах, здесь не применяй."
)


def skill_body(content: str) -> str:
    """Текст скилла без frontmatter: name/description нужны агенту, а не модели."""
    return _FRONTMATTER.sub("", content, count=1).strip()


def with_skills(template: str, skills: list[tuple[str, str]]) -> str:
    """Дописать скиллы в промпт.

    Если в промпте есть {{skills}}, блок встаёт туда — так пользователь сам решает,
    где правила окажутся относительно данных. Иначе блок идёт в конец.
    """
    if not skills:
        return template.replace("{{skills}}", "")
    parts = [
        _SKILLS_HEADER,
        *(f"=== {name} ===\n{skill_body(content)}" for name, content in skills),
    ]
    block = "\n\n".join(parts)
    if "{{skills}}" in template:
        return template.replace("{{skills}}", block)
    return f"{template.rstrip()}\n\n{block}\n"


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
