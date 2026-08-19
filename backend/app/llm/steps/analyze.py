"""Шаг анализа вакансии — один вызов вместо двух (§15)."""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts, router
from app.llm.base import LLMResult
from app.llm.schemas import VacancyAnalysis


async def analyze_vacancy(
    session: AsyncSession,
    *,
    digest: dict[str, Any] | None,
    allowed_facts: str,
    title: str,
    company_name: str | None,
    description: str,
    max_vacancy_chars: int = 6000,
) -> tuple[VacancyAnalysis, LLMResult]:
    template = await prompts.get_text(session, PromptKey.ANALYZE)
    suspicious_rules = await prompts.get_text(session, PromptKey.SUSPICIOUS_RULES)

    prompt = prompts.render(
        template,
        {
            "resume_digest": _digest_text(digest),
            "allowed_facts": allowed_facts,
            "vacancy_title": title,
            "company_name": company_name,
            # Описание обрезается: контекст модели 8192 токена и его надо
            # делить с выжимкой и инструкциями (§2)
            "vacancy_description": description[:max_vacancy_chars],
            "suspicious_rules": suspicious_rules,
        },
    )

    provider = await router.provider_for_step(session, PromptKey.ANALYZE)
    try:
        return await router.call(provider, prompt, VacancyAnalysis)
    finally:
        await provider.close()


def _digest_text(digest: dict[str, Any] | None) -> str:
    if not digest:
        return "—"
    return json.dumps(digest, ensure_ascii=False, indent=1)
