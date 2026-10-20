"""Решение по вакансии (§15). Без LLM: только разбор уже полученных данных."""

from dataclasses import dataclass

from app.core.enums import BotMode, SkipReason, VacancyStatus
from app.llm.schemas import VacancyAnalysis


@dataclass(frozen=True, slots=True)
class DecisionInput:
    analysis: VacancyAnalysis
    min_score: int = 75
    auto_apply_score: int = 90
    company_score_delta: int = 0
    force_review: bool = False
    hard_filters_passed: bool = True
    hard_filter_reason: SkipReason | None = None
    hard_filter_details: str | None = None
    hard_suspicious_reasons: tuple[str, ...] = ()
    mode: str = BotMode.MANUAL
    answer_employer_questions: bool = False
    already_applied: bool = False
    # Широкий охват: «не справится» и «нет критического навыка» не отсекают
    # вакансию сами по себе — на частичное совпадение откликаться выгоднее,
    # недостающее учат до собеседования. Решает оценка
    broad: bool = False


@dataclass(frozen=True, slots=True)
class Decision:
    status: VacancyStatus
    skip_reason: SkipReason | None = None
    skip_details: str | None = None
    score: int = 0
    suspicious_reasons: tuple[str, ...] = ()


def decide(data: DecisionInput) -> Decision:
    """Порядок проверок важен: он определяет, какую причину увидит пользователь."""
    analysis = data.analysis
    score = max(0, min(100, analysis.score + data.company_score_delta))

    if data.already_applied:
        return Decision(
            VacancyStatus.APPLIED,
            SkipReason.ALREADY_APPLIED,
            "Отклик на эту вакансию уже отправлялся",
            score,
        )

    if not data.hard_filters_passed:
        return Decision(
            VacancyStatus.FILTERED_OUT,
            data.hard_filter_reason,
            data.hard_filter_details,
            score,
        )

    # Подозрительная вакансия не выбрасывается: её должно быть видно глазами (§13)
    suspicious = tuple(data.hard_suspicious_reasons) + tuple(analysis.suspicious_reasons)
    if analysis.is_suspicious or data.hard_suspicious_reasons:
        return Decision(
            VacancyStatus.SUSPICIOUS,
            SkipReason.SUSPICIOUS,
            "; ".join(suspicious) or "Признаки развода",
            score,
            suspicious,
        )

    if not analysis.profession_match:
        return Decision(
            VacancyStatus.REJECTED_BY_AI,
            SkipReason.PROFESSION_MISMATCH,
            analysis.reason or "Другая профессия",
            score,
        )

    if not analysis.can_do_job and not data.broad:
        return Decision(
            VacancyStatus.REJECTED_BY_AI,
            SkipReason.CANNOT_DO_JOB,
            analysis.reason or "Не сможет выполнять обязанности",
            score,
        )

    if analysis.critical_missing and not data.broad:
        return Decision(
            VacancyStatus.REJECTED_BY_AI,
            SkipReason.CRITICAL_SKILL_MISSING,
            "Нет критических навыков: " + ", ".join(analysis.critical_missing),
            score,
        )

    if score < data.min_score:
        return Decision(
            VacancyStatus.REJECTED_BY_AI,
            SkipReason.LOW_SCORE,
            f"Оценка {score} ниже порога {data.min_score}",
            score,
        )

    # В широком режиме вопросы из описания закрывает письмо; чего нет в резюме,
    # оно оставит заглушкой, и такое письмо само не уйдёт
    if (
        analysis.employer_questions_detected
        and not data.answer_employer_questions
        and not data.broad
    ):
        return Decision(
            VacancyStatus.NEEDS_DATA,
            None,
            "В вакансии есть вопросы работодателя, ответы на них выключены в настройках",
            score,
        )

    if data.force_review:
        return Decision(
            VacancyStatus.REVIEW_REQUIRED, None, "Правило по компании: всегда на проверку", score
        )

    if score < data.auto_apply_score:
        return Decision(VacancyStatus.REVIEW_REQUIRED, None, None, score)

    # Порог автоотклика взят, но нажимать за пользователя вправе только автомат
    if data.mode == BotMode.AUTO:
        return Decision(VacancyStatus.LETTER_READY, None, None, score)
    return Decision(VacancyStatus.RECOMMENDED, None, None, score)
