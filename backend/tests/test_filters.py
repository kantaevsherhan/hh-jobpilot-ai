"""Остальные hard-фильтры и правила компаний (§11, §12, §30)."""

from datetime import UTC, datetime, timedelta

from app.core.enums import CompanyRuleAction, MatchType, RemoteMode, SkipReason, WorkFormat
from app.filters.age import check_age
from app.filters.company import CompanyRuleSpec, check_company
from app.filters.engine import run_filters
from app.filters.experience import check_experience
from app.filters.keywords import check_keywords
from app.filters.suspicious import check_suspicious
from app.filters.work_format import check_work_format
from tests.factories import make_facts, make_rules

NOW = datetime(2026, 8, 20, tzinfo=UTC)


class TestФорматРаботы:
    def test_офис_не_проходит_при_только_удалёнке(self) -> None:
        result = check_work_format(WorkFormat.OFFICE, RemoteMode.REMOTE_ONLY)

        assert result.passed is False
        assert result.reason == SkipReason.WORK_FORMAT

    def test_гибрид_проходит_при_удалёнке_или_гибриде(self) -> None:
        assert check_work_format(WorkFormat.HYBRID, RemoteMode.REMOTE_OR_HYBRID).passed is True
        assert check_work_format(WorkFormat.HYBRID, RemoteMode.REMOTE_ONLY).passed is False

    def test_неизвестный_формат_не_отсекается(self) -> None:
        result = check_work_format(WorkFormat.UNKNOWN, RemoteMode.REMOTE_ONLY)

        assert result.passed is True
        assert result.note is not None

    def test_режим_любой_пропускает_всё(self) -> None:
        assert check_work_format(WorkFormat.OFFICE, RemoteMode.ANY).passed is True


class TestСвежесть:
    def test_старая_вакансия_отсекается(self) -> None:
        result = check_age(NOW - timedelta(days=30), 7, now=NOW)

        assert result.passed is False
        assert result.reason == SkipReason.TOO_OLD

    def test_свежая_проходит(self) -> None:
        assert check_age(NOW - timedelta(days=2), 7, now=NOW).passed is True

    def test_без_даты_публикации_не_отсекаем(self) -> None:
        assert check_age(None, 7, now=NOW).passed is True


class TestКлючевыеСлова:
    def test_стоп_слово_в_заголовке(self) -> None:
        result = check_keywords(title="Разработчик 1С", exclude=["1С", "Bitrix"])

        assert result.passed is False
        assert result.reason == SkipReason.KEYWORD_STOP

    def test_стоп_слово_регистронезависимо(self) -> None:
        assert check_keywords(title="WordPress Developer", exclude=["wordpress"]).passed is False

    def test_стоп_слово_в_описании(self) -> None:
        result = check_keywords(title="Backend", description="Работа с Bitrix", exclude=["bitrix"])

        assert result.passed is False

    def test_обязательное_слово_отсутствует(self) -> None:
        result = check_keywords(title="Python Developer", include=["Node.js", "TypeScript"])

        assert result.passed is False
        assert result.reason == SkipReason.KEYWORD_MISSING

    def test_достаточно_одного_обязательного_слова(self) -> None:
        assert check_keywords(title="Node.js Developer", include=["Node.js", "Go"]).passed is True


class TestОпыт:
    def test_неподходящий_диапазон_отсекается(self) -> None:
        result = check_experience("Более 6 лет", ["between1And3", "between3And6"])

        assert result.passed is False
        assert result.reason == SkipReason.EXPERIENCE

    def test_подходящий_диапазон_проходит(self) -> None:
        assert check_experience("От 3 до 6 лет", ["between3And6"]).passed is True

    def test_нераспознанный_опыт_не_отсекается(self) -> None:
        assert check_experience("Уровень джедая", ["between3And6"]).passed is True


class TestПравилаКомпаний:
    def test_contains_ловит_подстроку_в_любом_регистре(self) -> None:
        rule = CompanyRuleSpec(
            match_type=MatchType.CONTAINS, value="vash", action=CompanyRuleAction.SKIP
        )

        for name in ("Vash Group", "VASH COMPANY", "ТОО Vash"):
            verdict = check_company(name, [rule])
            assert verdict.result.passed is False, name
            assert verdict.result.reason == SkipReason.COMPANY_RULE

    def test_contains_не_срабатывает_на_чужой_компании(self) -> None:
        rule = CompanyRuleSpec(
            match_type=MatchType.CONTAINS, value="vash", action=CompanyRuleAction.SKIP
        )

        assert check_company("ТОО Прогресс", [rule]).result.passed is True

    def test_equals_требует_полного_совпадения(self) -> None:
        rule = CompanyRuleSpec(
            match_type=MatchType.EQUALS, value="Kaspi", action=CompanyRuleAction.SKIP
        )

        assert check_company("Kaspi", [rule]).result.passed is False
        assert check_company("Kaspi Bank", [rule]).result.passed is True

    def test_учёт_регистра_включается_настройкой(self) -> None:
        rule = CompanyRuleSpec(
            match_type=MatchType.CONTAINS,
            value="VASH",
            action=CompanyRuleAction.SKIP,
            case_sensitive=True,
        )

        assert check_company("vash group", [rule]).result.passed is True
        assert check_company("VASH group", [rule]).result.passed is False

    def test_бонус_и_штраф_суммируются(self) -> None:
        rules = [
            CompanyRuleSpec(MatchType.CONTAINS, "abc", CompanyRuleAction.BOOST, score_delta=20),
            CompanyRuleSpec(MatchType.CONTAINS, "тоо", CompanyRuleAction.PENALTY, score_delta=-5),
        ]

        verdict = check_company("ТОО ABC", rules)

        assert verdict.result.passed is True
        assert verdict.score_delta == 15

    def test_всегда_на_проверку_не_отсекает_но_помечает(self) -> None:
        rule = CompanyRuleSpec(MatchType.CONTAINS, "abc", CompanyRuleAction.ALWAYS_REVIEW)

        verdict = check_company("ТОО ABC", [rule])

        assert verdict.result.passed is True
        assert verdict.force_review is True


class TestСкамДетект:
    def test_короткое_описание(self) -> None:
        reasons = check_suspicious(title="Менеджер", description="Звоните", company_name="ТОО ABC")

        assert any("короче" in reason for reason in reasons)

    def test_компания_не_указана(self) -> None:
        reasons = check_suspicious(title="Менеджер", description="x" * 400, company_name=None)

        assert "Компания не указана" in reasons

    def test_частное_лицо(self) -> None:
        reasons = check_suspicious(
            title="Курьер", description="x" * 400, company_name="Частное лицо"
        )

        assert any("частное лицо" in reason.lower() for reason in reasons)

    def test_только_мессенджер_без_требований(self) -> None:
        description = "Ищем сотрудников. Пишите в WhatsApp по номеру. " * 10

        reasons = check_suspicious(title="Работа", description=description, company_name="ТОО ABC")

        assert any("мессенджер" in reason for reason in reasons)

    def test_мессенджер_при_наличии_требований_не_повод(self) -> None:
        description = (
            "Требования: опыт работы с Node.js от 3 лет, PostgreSQL, Docker. "
            "Обязанности: разработка API. Пишите в Telegram для связи. "
        ) * 4

        reasons = check_suspicious(title="Backend", description=description, company_name="ТОО ABC")

        assert reasons == []

    def test_внешняя_форма_отклика(self) -> None:
        reasons = check_suspicious(
            title="Backend",
            description="Требования: опыт. " * 40,
            company_name="ТОО ABC",
            apply_is_external=True,
        )

        assert any("внешний сайт" in reason for reason in reasons)

    def test_нормальная_вакансия_чистая(self) -> None:
        reasons = check_suspicious(
            title="Backend Developer",
            description="Требования: Node.js, PostgreSQL, Docker. Обязанности: разработка. " * 8,
            company_name="ТОО ABC",
        )

        assert reasons == []


class TestДвижок:
    def test_первая_непройденная_проверка_даёт_причину(self) -> None:
        result = run_filters(
            make_facts(title="Разработчик 1С"),
            make_rules(exclude_keywords=["1С"]),
            now=NOW,
        )

        assert result.passed is False
        assert result.reason == SkipReason.KEYWORD_STOP

    def test_вакансия_проходит_все_проверки(self) -> None:
        result = run_filters(
            make_facts(),
            make_rules(min_salary=500_000, remote_mode=RemoteMode.REMOTE_ONLY),
            now=NOW,
        )

        assert result.passed is True
        assert result.reason is None

    def test_правило_компании_отсекает_до_остальных_проверок(self) -> None:
        rule = CompanyRuleSpec(MatchType.CONTAINS, "abc", CompanyRuleAction.SKIP)

        result = run_filters(make_facts(), make_rules(), [rule], now=NOW)

        assert result.passed is False
        assert result.reason == SkipReason.COMPANY_RULE

    def test_обязательные_слова_не_проверяются_до_открытия_карточки(self) -> None:
        # В выдаче описания ещё нет: отсекать по обязательным словам рано
        result = run_filters(
            make_facts(description=""),
            make_rules(include_keywords=["Kubernetes"]),
            now=NOW,
        )

        assert result.passed is True

    def test_штраф_компании_доезжает_до_результата(self) -> None:
        rule = CompanyRuleSpec(
            MatchType.CONTAINS, "abc", CompanyRuleAction.PENALTY, score_delta=-10
        )

        result = run_filters(make_facts(), make_rules(), [rule], now=NOW)

        assert result.passed is True
        assert result.score_delta == -10
