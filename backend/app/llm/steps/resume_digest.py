"""Шаг «выжимка резюме» (§7)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts, router
from app.llm.base import LLMResult
from app.llm.schemas import ResumeDigest


async def build_digest(session: AsyncSession, resume_text: str) -> tuple[ResumeDigest, LLMResult]:
    template = await prompts.get_text(session, PromptKey.RESUME_DIGEST)
    prompt = prompts.render(template, {"resume_text": resume_text})
    provider = await router.provider_for_step(session, PromptKey.RESUME_DIGEST)
    try:
        return await router.call(provider, prompt, ResumeDigest)
    finally:
        await provider.close()


def digest_to_skills(digest: ResumeDigest) -> list[tuple[str, bool]]:
    """Разложить выжимку в плоский список навыков: (название, ключевой).

    Нужно не модели, а hard-фильтрам и статистике (§7).
    """
    seen: dict[str, bool] = {}
    for name in digest.core_stack:
        seen.setdefault(name.strip(), True)
    for name in digest.additional:
        seen.setdefault(name.strip(), False)
    return [(name, is_core) for name, is_core in seen.items() if name]
