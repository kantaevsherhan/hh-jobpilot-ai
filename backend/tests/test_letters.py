"""Скрытые инструкции, словарная проверка фактов, личные данные (§16, §18, §19)."""

from app.core.personal_data import find_personal_data_request, is_allowed_field
from app.llm.steps.fact_check import dictionary_check
from app.llm.steps.letter import (
    call_with_min_length,
    check_instructions_followed,
    pick_language,
    required_words,
)
from tests.fakes import FakeProvider


class TestСкрытыеИнструкции:
    def test_слово_в_кавычках_вытаскивается(self) -> None:
        instructions = ["написать в сопроводительном слово «Сыр»"]

        assert required_words(instructions) == ["Сыр"]

    def test_разные_виды_кавычек(self) -> None:
        instructions = ['укажите код "ALPHA-7"', "добавьте слово 'Море'"]

        assert set(required_words(instructions)) == {"ALPHA-7", "Море"}

    def test_инструкция_без_конкретного_слова_не_проверяется_кодом(self) -> None:
        assert required_words(["указать в начале письма желаемую зарплату"]) == []

    def test_невыполненная_инструкция_находится(self) -> None:
        missing = check_instructions_followed(
            "Здравствуйте! Хочу откликнуться на вакансию.", ["напишите слово «Сыр»"]
        )

        assert missing == ["Сыр"]

    def test_выполненная_инструкция_проходит(self) -> None:
        missing = check_instructions_followed(
            "Здравствуйте! Сыр. Хочу откликнуться.", ["напишите слово «Сыр»"]
        )

        assert missing == []

    def test_проверка_регистронезависима(self) -> None:
        assert check_instructions_followed("сыр в начале письма", ["слово «Сыр»"]) == []


class TestЯзыкПисьма:
    def test_язык_берётся_из_описания_вакансии(self) -> None:
        assert pick_language("kk", ["ru", "kk"]) == "kk"

    def test_неразрешённый_язык_заменяется_русским(self) -> None:
        assert pick_language("en", ["ru", "kk"]) == "ru"

    def test_при_пустом_языке_описания_берётся_русский(self) -> None:
        assert pick_language(None, ["ru", "en"]) == "ru"

    def test_если_русского_нет_берётся_первый_разрешённый(self) -> None:
        assert pick_language("en", ["kk"]) == "kk"


class TestСловарнаяПроверкаФактов:
    def test_выдуманная_технология_находится(self) -> None:
        unsupported = dictionary_check(
            "Имею большой опыт с AWS и Kubernetes.",
            resume_text="Node.js, PostgreSQL, Docker",
            allowed_facts="",
            resume_skills=["Node.js", "PostgreSQL", "Docker"],
        )

        assert set(unsupported) == {"AWS", "Kubernetes"}

    def test_технология_из_резюме_не_считается_выдумкой(self) -> None:
        unsupported = dictionary_check(
            "Работал с Docker и PostgreSQL.",
            resume_text="Node.js, PostgreSQL, Docker",
            allowed_facts="",
            resume_skills=["Docker"],
        )

        assert unsupported == []

    def test_технология_из_allowed_facts_разрешена(self) -> None:
        unsupported = dictionary_check(
            "Изучаю Kubernetes.",
            resume_text="Node.js",
            allowed_facts="Прохожу курс по Kubernetes",
            resume_skills=[],
        )

        assert unsupported == []

    def test_подстрока_не_даёт_ложного_срабатывания(self) -> None:
        # «Go» не должен находиться внутри слова «Google» или «говорю»
        unsupported = dictionary_check(
            "Говорю по-английски, использую Google Workspace.",
            resume_text="Node.js",
            allowed_facts="",
            resume_skills=[],
        )

        assert "Go" not in unsupported


class TestЛичныеДанные:
    def test_паспорт_запрещён(self) -> None:
        assert find_personal_data_request("Укажите номер паспорта") == "номер паспорта"

    def test_иин_запрещён(self) -> None:
        assert find_personal_data_request("Напишите ваш ИИН") == "ИИН"

    def test_банковские_реквизиты_запрещены(self) -> None:
        assert find_personal_data_request("Номер карты для выплат") == "банковские реквизиты"

    def test_адрес_проживания_запрещён(self) -> None:
        assert find_personal_data_request("Адрес проживания") == "адрес проживания"

    def test_фото_с_документом_запрещено(self) -> None:
        assert find_personal_data_request("Пришлите фото с документом") == "фото документа"

    def test_обычный_вопрос_разрешён(self) -> None:
        assert find_personal_data_request("Сколько лет опыта с Node.js?") is None

    def test_телефон_и_город_подставлять_можно(self) -> None:
        assert is_allowed_field("Ваш телефон") is True
        assert is_allowed_field("Город проживания") is True
        assert is_allowed_field("Номер паспорта") is False


class TestРеальныйСлучайВыдумки:
    """Случай с живого прогона: локальная 4B не заметила выдумку.

    Модель дописала в письмо Prisma ORM, OAuth и JWT, которых в резюме нет,
    и LLM-проверка признала письмо валидным. Поймать это должна словарная
    проверка — она детерминированная и бесплатная (§18).
    """

    LETTER = (
        "Настроен на работу с Docker и PostgreSQL, включая использование Prisma ORM. "
        "Имею практический опыт с аутентификацией (OAuth, JWT)."
    )
    RESUME = "Fullstack, 4 года. TypeScript, Vue, Node.js, NestJS, Go, PostgreSQL, Docker."

    def test_orm_и_протоколы_аутентификации_находятся(self) -> None:
        unsupported = dictionary_check(
            self.LETTER,
            resume_text=self.RESUME,
            allowed_facts="",
            resume_skills=["Node.js", "Docker", "PostgreSQL"],
        )

        assert set(unsupported) == {"Prisma", "OAuth", "JWT"}

    def test_то_что_в_резюме_есть_выдумкой_не_считается(self) -> None:
        unsupported = dictionary_check(
            "Работал с Docker, PostgreSQL и NestJS.",
            resume_text=self.RESUME,
            allowed_facts="",
            resume_skills=[],
        )

        assert unsupported == []


class TestДлинаПисьма:
    async def test_короткое_письмо_переписывается_один_раз(self) -> None:
        provider = FakeProvider({"letter": "Коротко."}, {"letter": "Длиннее " * 60})

        letter, _ = await call_with_min_length(provider, "промпт", min_chars=400)

        assert len(letter.letter) >= 400
        assert len(provider.prompts) == 2
        assert "СЛИШКОМ КОРОТКИЙ" in provider.prompts[1]

    async def test_письмо_нормальной_длины_не_переписывается(self) -> None:
        provider = FakeProvider({"letter": "а" * 390})

        await call_with_min_length(provider, "промпт", min_chars=400)

        assert len(provider.prompts) == 1

    async def test_если_повтор_ещё_короче_остаётся_первый_вариант(self) -> None:
        provider = FakeProvider({"letter": "Первый вариант."}, {"letter": "Ещё."})

        letter, _ = await call_with_min_length(provider, "промпт", min_chars=400)

        assert letter.letter == "Первый вариант."
