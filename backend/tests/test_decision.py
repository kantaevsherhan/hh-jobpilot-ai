"""Движок решений: каждая ветка §15 отдельным тестом."""

from app.core.enums import BotMode, SkipReason, VacancyStatus
from app.llm.schemas import VacancyAnalysis
from app.pipeline.decision import DecisionInput, decide


def make_analysis(**overrides: object) -> VacancyAnalysis:
    data: dict[str, object] = {
        "profession_match": True,
        "can_do_job": True,
        "score": 85,
        "critical_missing": [],
        "is_suspicious": False,
        "employer_questions_detected": False,
        "reason": "Стек совпадает",
    }
    data.update(overrides)
    return VacancyAnalysis.model_validate(data)


def decide_with(**overrides: object):
    analysis = overrides.pop("analysis", make_analysis())
    return decide(DecisionInput(analysis=analysis, **overrides))  # type: ignore[arg-type]


def test_непройденные_hard_фильтры_дают_отклонена_фильтром() -> None:
    decision = decide_with(
        hard_filters_passed=False,
        hard_filter_reason=SkipReason.SALARY_TOO_LOW,
        hard_filter_details="300 000 против 500 000",
    )

    assert decision.status == VacancyStatus.FILTERED_OUT
    assert decision.skip_reason == SkipReason.SALARY_TOO_LOW


def test_подозрительная_не_теряется_а_помечается() -> None:
    decision = decide_with(
        analysis=make_analysis(is_suspicious=True, suspicious_reasons=["Требуют оформить ИП"])
    )

    assert decision.status == VacancyStatus.SUSPICIOUS
    assert "Требуют оформить ИП" in decision.suspicious_reasons


def test_жёсткие_признаки_скама_перевешивают_мнение_модели() -> None:
    decision = decide_with(hard_suspicious_reasons=("Компания не указана",))

    assert decision.status == VacancyStatus.SUSPICIOUS


def test_другая_профессия() -> None:
    decision = decide_with(analysis=make_analysis(profession_match=False))

    assert decision.status == VacancyStatus.REJECTED_BY_AI
    assert decision.skip_reason == SkipReason.PROFESSION_MISMATCH


def test_не_сможет_выполнять_обязанности() -> None:
    decision = decide_with(analysis=make_analysis(can_do_job=False))

    assert decision.skip_reason == SkipReason.CANNOT_DO_JOB


def test_критически_отсутствующий_навык() -> None:
    decision = decide_with(analysis=make_analysis(critical_missing=["Kubernetes"]))

    assert decision.skip_reason == SkipReason.CRITICAL_SKILL_MISSING
    assert "Kubernetes" in (decision.skip_details or "")


def test_низкая_оценка() -> None:
    decision = decide_with(analysis=make_analysis(score=50), min_score=75)

    assert decision.skip_reason == SkipReason.LOW_SCORE


def test_штраф_компании_опускает_оценку_ниже_порога() -> None:
    decision = decide_with(analysis=make_analysis(score=80), min_score=75, company_score_delta=-10)

    assert decision.score == 70
    assert decision.skip_reason == SkipReason.LOW_SCORE


def test_бонус_компании_поднимает_до_рекомендации() -> None:
    decision = decide_with(
        analysis=make_analysis(score=85), auto_apply_score=90, company_score_delta=20
    )

    assert decision.score == 100
    assert decision.status == VacancyStatus.RECOMMENDED


def test_оценка_между_порогами_идёт_на_проверку() -> None:
    decision = decide_with(analysis=make_analysis(score=80), min_score=75, auto_apply_score=90)

    assert decision.status == VacancyStatus.REVIEW_REQUIRED


def test_вопросы_работодателя_при_выключенных_ответах() -> None:
    decision = decide_with(analysis=make_analysis(employer_questions_detected=True))

    assert decision.status == VacancyStatus.NEEDS_DATA


def test_вопросы_работодателя_при_включённых_ответах_не_мешают() -> None:
    decision = decide_with(
        analysis=make_analysis(score=95, employer_questions_detected=True),
        answer_employer_questions=True,
        mode=BotMode.AUTO,
    )

    assert decision.status == VacancyStatus.LETTER_READY


def test_правило_всегда_на_проверку() -> None:
    decision = decide_with(analysis=make_analysis(score=95), force_review=True)

    assert decision.status == VacancyStatus.REVIEW_REQUIRED


def test_высокая_оценка_в_ручном_режиме_только_рекомендует() -> None:
    decision = decide_with(analysis=make_analysis(score=95), mode=BotMode.MANUAL)

    assert decision.status == VacancyStatus.RECOMMENDED


def test_высокая_оценка_в_полуавтомате_тоже_только_рекомендует() -> None:
    decision = decide_with(analysis=make_analysis(score=95), mode=BotMode.SEMI_AUTO)

    assert decision.status == VacancyStatus.RECOMMENDED


def test_высокая_оценка_в_автомате_ведёт_к_письму() -> None:
    decision = decide_with(analysis=make_analysis(score=95), mode=BotMode.AUTO)

    assert decision.status == VacancyStatus.LETTER_READY


def test_уже_откликались_перевешивает_всё() -> None:
    decision = decide_with(
        analysis=make_analysis(score=99), mode=BotMode.AUTO, already_applied=True
    )

    assert decision.status == VacancyStatus.APPLIED
    assert decision.skip_reason == SkipReason.ALREADY_APPLIED


def test_оценка_не_выходит_за_границы() -> None:
    assert decide_with(analysis=make_analysis(score=95), company_score_delta=50).score == 100
    assert decide_with(analysis=make_analysis(score=5), company_score_delta=-50).score == 0


class TestШирокийОхват:
    """На частичное совпадение откликаться выгоднее: отвечают на 5 откликов из 100."""

    def test_не_справится_не_отсекает_если_оценка_проходит(self) -> None:
        decision = decide_with(
            analysis=make_analysis(can_do_job=False, score=65),
            broad=True,
            min_score=60,
            auto_apply_score=70,
        )

        assert decision.status == VacancyStatus.REVIEW_REQUIRED

    def test_нехватка_навыка_не_отсекает(self) -> None:
        decision = decide_with(
            analysis=make_analysis(critical_missing=["Kafka"], score=75),
            broad=True,
            min_score=60,
            auto_apply_score=70,
            mode=BotMode.AUTO,
        )

        assert decision.status == VacancyStatus.LETTER_READY

    def test_вопросы_из_описания_закрывает_письмо(self) -> None:
        decision = decide_with(
            analysis=make_analysis(employer_questions_detected=True, score=80),
            broad=True,
            min_score=60,
            auto_apply_score=70,
            mode=BotMode.AUTO,
        )

        assert decision.status == VacancyStatus.LETTER_READY

    def test_чужая_профессия_отсекается_всегда(self) -> None:
        # Разработчику не нужны отклики на слесаря, сколько бы ни было охвата
        decision = decide_with(analysis=make_analysis(profession_match=False), broad=True)

        assert decision.skip_reason == SkipReason.PROFESSION_MISMATCH

    def test_низкая_оценка_отсекается_и_в_широком_режиме(self) -> None:
        decision = decide_with(
            analysis=make_analysis(can_do_job=False, score=30), broad=True, min_score=60
        )

        assert decision.skip_reason == SkipReason.LOW_SCORE
