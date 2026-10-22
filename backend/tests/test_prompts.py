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
    # Насколько смело подавать опыт, решает регулятор: правила подставляются по уровню
    assert "{{embellishment_rules}}" in letter


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


class TestРегуляторПриукрашивания:
    def test_по_умолчанию_умеренно(self) -> None:
        from app.llm import embellishment

        assert embellishment.normalize(None) == embellishment.MODERATE
        assert embellishment.normalize("что-то") == embellishment.MODERATE

    def test_выдумка_запрещена_на_любом_уровне(self) -> None:
        from app.llm import embellishment

        for level in embellishment.LEVELS:
            assert "Никогда не выдумывай компании" in embellishment.LETTER_RULES[level]

    def test_строгий_уровень_не_усиливает_формулировки(self) -> None:
        from app.llm import embellishment

        assert "«участвовал» не становится «руководил»" in embellishment.LETTER_RULES["strict"]

    def test_словарь_не_блокирует_только_смелый_уровень(self) -> None:
        from app.llm.steps.fact_check import dictionary_blocks

        assert dictionary_blocks("strict") and dictionary_blocks("moderate")
        assert not dictionary_blocks("bold")

    async def test_уровень_берётся_из_настроек(self, session: AsyncSession) -> None:
        from app.llm import embellishment
        from app.storage.repositories import settings as settings_repo

        await settings_repo.put(session, "llm", {"letter_embellishment": "bold"})

        assert await embellishment.current_level(session) == "bold"

    def test_проверка_фактов_знает_про_уровень(self) -> None:
        assert "{{embellishment_rules}}" in prompts.default_text(PromptKey.FACT_CHECK)


def test_письмо_называет_стек_вакансии_без_очевидного() -> None:
    letter = prompts.default_text(PromptKey.LETTER)

    assert "основные технологии из требований вакансии" in letter
    # HTML и CSS в письме разработчику — шум
    assert "HTML, CSS" in letter


EXAMPLES = [
    ("Fullstack (Vue + Node.js) Fullstack", "vue", True),
    ("Backend (Node.js) Backend", "node", False),
    ("Frontend (Vue / Nuxt) Frontend", "front", False),
    ("Java Backend (Spring Boot) Энтерпрайз", "java", False),
    ("Backend (Go) Go", "go", False),
]


def test_на_java_вакансию_первым_идёт_пример_про_spring() -> None:
    from app.llm.steps.letter import pick_examples

    picked = pick_examples(EXAMPLES, "Java разработчик", "Spring Boot, PostgreSQL, Kafka")

    assert picked[0] == "java"
    assert len(picked) == 3


def test_go_не_находится_внутри_других_слов() -> None:
    from app.llm.steps.letter import pick_examples

    assert pick_examples(EXAMPLES, "Аналитик", "Работа с Google Cloud")[0] == "vue"
    assert pick_examples(EXAMPLES, "Golang developer", "Микросервисы")[0] == "go"


def test_без_совпадений_порядок_прежний() -> None:
    from app.llm.steps.letter import pick_examples

    assert pick_examples(EXAMPLES, "Аналитик", "Excel") == ["vue", "node", "front"]
