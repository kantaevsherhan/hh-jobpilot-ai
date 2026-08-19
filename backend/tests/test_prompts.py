"""Загрузка промптов и подстановка переменных (§33 п.18)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts
from app.llm.schemas import ResumeDigest
from app.llm.steps.resume_digest import digest_to_skills
from app.storage.models import Prompt


async def test_дефолтные_промпты_загружаются_один_раз(session: AsyncSession) -> None:
    added = await prompts.seed_defaults(session)
    again = await prompts.seed_defaults(session)

    assert added == len(PromptKey)
    assert again == 0


async def test_правка_промпта_переживает_повторный_seed(session: AsyncSession) -> None:
    await prompts.seed_defaults(session)
    row = await session.get_one(Prompt, 1)
    row.content = "мой промпт"
    await session.commit()

    await prompts.seed_defaults(session)

    assert await prompts.get_text(session, row.key) == "мой промпт"


def test_подстановка_переменных() -> None:
    rendered = prompts.render(
        "Кандидат: {{name}}\nНавыки:\n{{skills}}\nФакты: {{facts}}",
        {"name": "Шерхан", "skills": ["Go", "Vue"], "facts": ""},
    )

    assert "Кандидат: Шерхан" in rendered
    assert "- Go\n- Vue" in rendered
    # Пустая переменная не должна утечь в промпт как литерал
    assert "{{" not in rendered
    assert "Факты: —" in rendered


def test_выжимка_раскладывается_в_навыки() -> None:
    digest = ResumeDigest(core_stack=["TypeScript", "Go"], additional=["Docker", "Go"])

    skills = digest_to_skills(digest)

    assert ("TypeScript", True) in skills
    assert ("Docker", False) in skills
    # Go есть в обоих списках, но навык один и он ключевой
    assert [name for name, _ in skills].count("Go") == 1
    assert ("Go", True) in skills
