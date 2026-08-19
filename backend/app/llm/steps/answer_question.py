"""Ответы на вопросы работодателя (§19)."""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts, router
from app.llm.base import LLMResult
from app.llm.schemas import AnswerResponse


async def answer_question(
    session: AsyncSession,
    *,
    question: str,
    digest: dict[str, Any] | None,
    resume_text: str,
    allowed_facts: str,
) -> tuple[AnswerResponse, LLMResult]:
    template = await prompts.get_text(session, PromptKey.ANSWER_QUESTION)
    prompt = prompts.render(
        template,
        {
            "question": question,
            "resume_digest": json.dumps(digest, ensure_ascii=False, indent=1) if digest else "—",
            "resume_text": resume_text,
            "allowed_facts": allowed_facts,
        },
    )
    provider = await router.provider_for_step(session, PromptKey.ANSWER_QUESTION)
    try:
        return await router.call(provider, prompt, AnswerResponse)
    finally:
        await provider.close()
