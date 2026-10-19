"""Скиллы: правила стиля дописываются только к выбранным промптам."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts
from app.storage.models import Skill

SKILL_MD = "---\nname: anti-ai\ndescription: служебное\n---\n\n# Anti-AI\nБез «важно отметить»."


def test_скилл_дописывается_в_конец_без_frontmatter() -> None:
    result = prompts.with_skills("Напиши письмо.", [("anti-ai", SKILL_MD)])

    assert result.startswith("Напиши письмо.")
    assert "=== anti-ai ===\n# Anti-AI" in result
    assert "description: служебное" not in result


def test_скилл_встаёт_на_место_метки() -> None:
    result = prompts.with_skills("Правила:\n{{skills}}\nДанные", [("s", "правило")])

    assert result.index("правило") < result.index("Данные")
    assert "{{skills}}" not in result


def test_без_скиллов_метка_исчезает() -> None:
    assert prompts.with_skills("А {{skills}}Б", []) == "А Б"


async def test_подключаются_только_включённые_и_к_своему_промпту(session: AsyncSession) -> None:
    await prompts.seed_defaults(session)
    session.add_all(
        [
            Skill(name="для письма", content="ПРАВИЛО-1", prompt_keys=[PromptKey.LETTER.value]),
            Skill(name="для анализа", content="ПРАВИЛО-2", prompt_keys=[PromptKey.ANALYZE.value]),
            Skill(
                name="выключен",
                content="ПРАВИЛО-3",
                prompt_keys=[PromptKey.LETTER.value],
                is_enabled=False,
            ),
        ]
    )
    await session.commit()

    letter = await prompts.get_text(session, PromptKey.LETTER)

    assert "ПРАВИЛО-1" in letter
    assert "ПРАВИЛО-2" not in letter
    assert "ПРАВИЛО-3" not in letter


async def test_к_правилам_подозрительности_скилл_не_подключить(client: AsyncClient) -> None:
    targets = (await client.get("/api/v1/skills/targets")).json()
    response = await client.post(
        "/api/v1/skills",
        json={"name": "x", "content": "y", "prompt_keys": [PromptKey.SUSPICIOUS_RULES.value]},
    )

    assert PromptKey.SUSPICIOUS_RULES.value not in [t["key"] for t in targets]
    assert response.status_code == 422


async def test_скилл_создаётся_и_правится(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/skills", json={"name": "anti-ai", "content": SKILL_MD, "prompt_keys": ["letter"]}
    )
    skill_id = created.json()["id"]

    patched = await client.patch(f"/api/v1/skills/{skill_id}", json={"is_enabled": False})

    assert created.status_code == 201
    assert patched.json()["is_enabled"] is False
    assert patched.json()["prompt_keys"] == ["letter"]
