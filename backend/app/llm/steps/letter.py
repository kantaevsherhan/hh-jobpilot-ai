"""Генерация сопроводительного письма (§17)."""

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts, router
from app.llm.base import LLMProvider, LLMResult
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
        return await call_with_style_check(provider, prompt, min_chars)
    finally:
        await provider.close()


# Небольшой недобор не стоит лишнего вызова модели: 390 символов при минимуме 400 — норма
SHORT_TOLERANCE = 0.8

# Двоеточие вне ссылок: «https://» и время «10:30» не считаются
_COLON = re.compile(r":(?!//)(?!\d)")


def style_problems(letter: str, min_chars: int) -> list[str]:
    """Что в письме нарушает правила, которые модели упорно игнорируют.

    Длину маленькие модели не держат, двоеточие ставят по привычке даже под запретом.
    """
    problems = []
    if len(letter) < min_chars * SHORT_TOLERANCE:
        problems.append(
            f"письмо слишком короткое, {len(letter)} символов, а нужно не меньше "
            f"{min_chars}. Раскрой главный факт и связь с задачами вакансии"
        )
    if _COLON.search(letter):
        problems.append("в письме есть двоеточие, а его быть не должно. Перестрой эти фразы")
    return problems


async def call_with_style_check(
    provider: LLMProvider, prompt: str, min_chars: int
) -> tuple[LetterResponse, LLMResult]:
    """Одна повторная попытка с перечнем нарушений почти всегда их чинит."""
    letter, result = await router.call(provider, prompt, LetterResponse)
    problems = style_problems(letter.letter, min_chars)
    if not problems:
        return letter, result

    retry_prompt = (
        f"{prompt}\n\nПЕРЕПИШИ ПРЕДЫДУЩИЙ ВАРИАНТ, ничего не выдумывая. Что не так. "
        + ". ".join(problems)
        + f".\n\n{letter.letter}"
    )
    fixed, fixed_result = await router.call(provider, retry_prompt, LetterResponse)
    # Повтор бывает хуже первого варианта — тогда оставляем первый
    before, after = len(problems), len(style_problems(fixed.letter, min_chars))
    if after < before or (after == before and len(fixed.letter) > len(letter.letter)):
        return fixed, fixed_result
    return letter, result
