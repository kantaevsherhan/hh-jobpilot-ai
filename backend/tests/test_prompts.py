"""Загрузка промптов и подстановка переменных (§33 п.18)."""

from sqlalchemy import select
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


async def test_на_пустой_базе_заводится_локальная_ollama(session: AsyncSession) -> None:
    from app.llm.prompts import seed_default_provider
    from app.storage.models import LLMProvider

    created = await seed_default_provider(session)
    again = await seed_default_provider(session)

    rows = list((await session.scalars(select(LLMProvider))).all())
    assert created is True
    assert again is False
    assert len(rows) == 1
    # Адрес, модель и num_ctx живут в строке провайдера, а не в .env
    assert rows[0].base_url == "http://localhost:11434"
    assert rows[0].model == "qwen3:4b-instruct"
    assert rows[0].extra_json["num_ctx"] == 8192


def test_дефолтные_промпты_требуют_русский_ответ() -> None:
    """Причины и флаги читает человек в интерфейсе, а он на русском (§8).

    Локальная модель охотно отвечает по-английски, если её не попросить.
    """
    analyze = prompts.default_text(PromptKey.ANALYZE)
    fact_check = prompts.default_text(PromptKey.FACT_CHECK)

    assert "по-русски" in analyze
    assert "reason" in analyze
    assert "по-русски" in fact_check


def test_промпт_письма_держит_все_переменные_и_запрет_штампов() -> None:
    letter = prompts.default_text(PromptKey.LETTER)

    for name in [
        "resume_digest",
        "resume_text",
        "allowed_facts",
        "hidden_instructions",
        "vacancy_description",
        "letter_examples",
        "min_chars",
        "max_chars",
        "language",
    ]:
        assert f"{{{{{name}}}}}" in letter
    # Правила против текста «как от нейросети» и против усиления фактов
    assert "важно отметить" in letter
    assert "«участвовал» не становится «руководил»" in letter


def test_проверка_фактов_видит_полное_резюме() -> None:
    """С одной выжимкой проверка считала выдумкой компании и сроки из резюме."""
    assert "{{resume_text}}" in prompts.default_text(PromptKey.FACT_CHECK)


async def test_встроенные_примеры_писем_добавляются_один_раз(session: AsyncSession) -> None:
    from app.storage.models import LetterExample

    added = await prompts.seed_letter_examples(session)
    for row in (await session.scalars(select(LetterExample))).all():
        await session.delete(row)
    await session.commit()
    again = await prompts.seed_letter_examples(session)

    assert added > 0
    # Пользователь удалил примеры — перезапуск их не возвращает
    assert again == 0


def test_встроенные_примеры_соблюдают_правила_письма() -> None:
    from app.core.letter_examples import DEFAULT_LETTER_EXAMPLES
    from app.llm.steps.fact_check import find_placeholders
    from app.llm.steps.letter import style_problems

    for example in DEFAULT_LETTER_EXAMPLES:
        content = example["content"]
        assert content.split("\n")[0].rstrip("!") in {"Здравствуйте", "Добрый день", "Привет"}
        # Двоеточий нет; длину не проверяем — среди примеров есть короткий
        assert not [p for p in style_problems(content, 0) if "двоеточие" in p], example["name"]
        # Подпись — заглушка, чтобы скопированное имя не ушло работодателю
        assert find_placeholders(content) == ["[Имя Фамилия]"], example["name"]
