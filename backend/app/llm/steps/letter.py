"""Генерация сопроводительного письма (§17)."""

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts, router
from app.llm.base import LLMResult
from app.llm.schemas import LetterResponse

# Слово в кавычках внутри скрытой инструкции — то, что должно оказаться в письме
QUOTED = re.compile(r"[«\"'`]([^»\"'`]{2,40})[»\"'`]")


def required_words(hidden_instructions: list[str]) -> list[str]:
    """Достать из инструкций конкретные слова, наличие которых проверяется кодом.

    Инструкция «напишите слово Сыр» проверяема, «будьте креативны» — нет.
    """
    words: list[str] = []
    for instruction in hidden_instructions:
        words.extend(match.strip() for match in QUOTED.findall(instruction))
    return [word for word in words if word]


def check_instructions_followed(letter: str, hidden_instructions: list[str]) -> list[str]:
    """Вернуть слова, которые требовались, но в письме их нет."""
    lowered = letter.lower()
    return [word for word in required_words(hidden_instructions) if word.lower() not in lowered]


def pick_language(description_lang: str | None, allowed: list[str]) -> str:
    """Язык письма — по языку описания вакансии, из числа разрешённых (§17).

    Заголовок не годится: в IT он часто английский при русском описании.
    """
    if not allowed:
        return "ru"
    if description_lang and description_lang in allowed:
        return description_lang
    return "ru" if "ru" in allowed else allowed[0]


async def write_letter(
    session: AsyncSession,
    *,
    digest: dict[str, Any] | None,
    resume_text: str,
    allowed_facts: str,
    title: str,
    company_name: str | None,
    description: str,
    matched_skills: list[str],
    green_flags: list[str],
    hidden_instructions: list[str],
    language: str,
    examples: list[str],
    min_chars: int,
    max_chars: int,
    max_vacancy_chars: int = 6000,
    extra_instruction: str | None = None,
) -> tuple[LetterResponse, LLMResult]:
    template = await prompts.get_text(session, PromptKey.LETTER)
    prompt = prompts.render(
        template,
        {
            "resume_digest": json.dumps(digest, ensure_ascii=False, indent=1) if digest else "—",
            "resume_text": resume_text,
            "allowed_facts": allowed_facts,
            "vacancy_title": title,
            "company_name": company_name,
            "vacancy_description": description[:max_vacancy_chars],
            "matched_skills": matched_skills,
            "green_flags": green_flags,
            "hidden_instructions": hidden_instructions,
            "language": language,
            "min_chars": min_chars,
            "max_chars": max_chars,
            "letter_examples": "\n\n---\n\n".join(examples[:3]),
        },
    )
    if extra_instruction:
        prompt += f"\n\nДОПОЛНИТЕЛЬНОЕ УКАЗАНИЕ: {extra_instruction}"

    provider = await router.provider_for_step(session, PromptKey.LETTER)
    try:
        return await router.call(provider, prompt, LetterResponse)
    finally:
        await provider.close()
