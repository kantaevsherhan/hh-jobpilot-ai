"""Справочники кодов (§24 ТЗ).

Коды хранятся в БД на английском, подписи для интерфейса — на русском
и лежат рядом с кодом, чтобы не расходились.
"""

from enum import StrEnum


class VacancyStatus(StrEnum):
    """Статус вакансии для конкретного резюме."""

    DISCOVERED = "DISCOVERED"
    FILTERED_OUT = "FILTERED_OUT"
    ANALYZING = "ANALYZING"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SUSPICIOUS = "SUSPICIOUS"
    REJECTED_BY_AI = "REJECTED_BY_AI"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    NEEDS_DATA = "NEEDS_DATA"
    NEEDS_USER_ACTION = "NEEDS_USER_ACTION"
    EXTERNAL_APPLY = "EXTERNAL_APPLY"
    LETTER_READY = "LETTER_READY"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    APPLY_PREPARED = "APPLY_PREPARED"
    APPLY_FAILED = "APPLY_FAILED"
    APPLY_UNKNOWN = "APPLY_UNKNOWN"
    SKIPPED_BY_USER = "SKIPPED_BY_USER"
    VACANCY_CLOSED = "VACANCY_CLOSED"
    PARSE_FAILED = "PARSE_FAILED"


VACANCY_STATUS_LABELS: dict[str, str] = {
    VacancyStatus.DISCOVERED: "Найдена",
    VacancyStatus.FILTERED_OUT: "Отклонена фильтром",
    VacancyStatus.ANALYZING: "Анализируется",
    VacancyStatus.ANALYSIS_FAILED: "Ошибка анализа",
    VacancyStatus.SUSPICIOUS: "Подозрительная",
    VacancyStatus.REJECTED_BY_AI: "Не подходит",
    VacancyStatus.REVIEW_REQUIRED: "На проверке",
    VacancyStatus.RECOMMENDED: "Рекомендована",
    VacancyStatus.NEEDS_DATA: "Нужны данные",
    VacancyStatus.NEEDS_USER_ACTION: "Нужно действие",
    VacancyStatus.EXTERNAL_APPLY: "Отклик на другом сайте",
    VacancyStatus.LETTER_READY: "Письмо готово",
    VacancyStatus.APPLYING: "Отправляется",
    VacancyStatus.APPLIED: "Отклик отправлен",
    VacancyStatus.APPLY_PREPARED: "Подготовлен (DRY_RUN)",
    VacancyStatus.APPLY_FAILED: "Ошибка отклика",
    VacancyStatus.APPLY_UNKNOWN: "Состояние неизвестно",
    VacancyStatus.SKIPPED_BY_USER: "Пропущена вручную",
    VacancyStatus.VACANCY_CLOSED: "Вакансия закрыта",
    VacancyStatus.PARSE_FAILED: "Не удалось прочитать",
}


class SkipReason(StrEnum):
    """Причина отклонения вакансии."""

    SALARY_TOO_LOW = "SALARY_TOO_LOW"
    SALARY_UNKNOWN = "SALARY_UNKNOWN"
    WORK_FORMAT = "WORK_FORMAT"
    EXPERIENCE = "EXPERIENCE"
    TOO_OLD = "TOO_OLD"
    KEYWORD_STOP = "KEYWORD_STOP"
    KEYWORD_MISSING = "KEYWORD_MISSING"
    COMPANY_RULE = "COMPANY_RULE"
    PROFESSION_MISMATCH = "PROFESSION_MISMATCH"
    CANNOT_DO_JOB = "CANNOT_DO_JOB"
    CRITICAL_SKILL_MISSING = "CRITICAL_SKILL_MISSING"
    LOW_SCORE = "LOW_SCORE"
    SUSPICIOUS = "SUSPICIOUS"
    DUPLICATE = "DUPLICATE"
    ALREADY_APPLIED = "ALREADY_APPLIED"
    VACANCY_CLOSED = "VACANCY_CLOSED"


SKIP_REASON_LABELS: dict[str, str] = {
    SkipReason.SALARY_TOO_LOW: "Зарплата ниже минимума",
    SkipReason.SALARY_UNKNOWN: "Зарплата не указана",
    SkipReason.WORK_FORMAT: "Неподходящий формат работы",
    SkipReason.EXPERIENCE: "Не подходит по опыту",
    SkipReason.TOO_OLD: "Вакансия старше указанного срока",
    SkipReason.KEYWORD_STOP: "Стоп-слово в описании",
    SkipReason.KEYWORD_MISSING: "Нет обязательного слова",
    SkipReason.COMPANY_RULE: "Правило по компании",
    SkipReason.PROFESSION_MISMATCH: "Другая профессия",
    SkipReason.CANNOT_DO_JOB: "Не сможет выполнять обязанности",
    SkipReason.CRITICAL_SKILL_MISSING: "Нет критического навыка",
    SkipReason.LOW_SCORE: "Низкая оценка соответствия",
    SkipReason.SUSPICIOUS: "Подозрительная вакансия",
    SkipReason.DUPLICATE: "Уже есть в базе",
    SkipReason.ALREADY_APPLIED: "Отклик уже отправлялся",
    SkipReason.VACANCY_CLOSED: "Вакансия закрыта",
}


class HHApplicationStatus(StrEnum):
    """Статус отклика на стороне HH."""

    SENT = "SENT"
    VIEWED = "VIEWED"
    INVITED = "INVITED"
    DECLINED = "DECLINED"
    NO_ANSWER = "NO_ANSWER"


HH_APPLICATION_STATUS_LABELS: dict[str, str] = {
    HHApplicationStatus.SENT: "Отправлен",
    HHApplicationStatus.VIEWED: "Просмотрен работодателем",
    HHApplicationStatus.INVITED: "Приглашение",
    HHApplicationStatus.DECLINED: "Отказ",
    HHApplicationStatus.NO_ANSWER: "Без ответа",
}


class ErrorCode(StrEnum):
    """Коды ошибок (§25)."""

    BROWSER_NOT_STARTED = "BROWSER_NOT_STARTED"
    BROWSER_SELECTOR_NOT_FOUND = "BROWSER_SELECTOR_NOT_FOUND"
    BROWSER_TIMEOUT = "BROWSER_TIMEOUT"
    HH_SESSION_EXPIRED = "HH_SESSION_EXPIRED"
    HH_CAPTCHA = "HH_CAPTCHA"
    HH_UNKNOWN_PAGE = "HH_UNKNOWN_PAGE"
    PARSE_FAILED = "PARSE_FAILED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    INVALID_LLM_RESPONSE = "INVALID_LLM_RESPONSE"
    FACT_CHECK_FAILED = "FACT_CHECK_FAILED"
    APPLY_FORM_UNKNOWN = "APPLY_FORM_UNKNOWN"
    APPLICATION_STATE_UNKNOWN = "APPLICATION_STATE_UNKNOWN"
    LIMIT_REACHED = "LIMIT_REACHED"
    PERSONAL_DATA_REQUESTED = "PERSONAL_DATA_REQUESTED"


ERROR_CODE_LABELS: dict[str, str] = {
    ErrorCode.BROWSER_NOT_STARTED: "Браузер не запущен",
    ErrorCode.BROWSER_SELECTOR_NOT_FOUND: "Не найден элемент на странице. Возможно, HH изменил вёрстку",
    ErrorCode.BROWSER_TIMEOUT: "Страница не ответила вовремя",
    ErrorCode.HH_SESSION_EXPIRED: "Сессия HH истекла, нужен вход",
    ErrorCode.HH_CAPTCHA: "HH показал капчу",
    ErrorCode.HH_UNKNOWN_PAGE: "Открылась неизвестная страница",
    ErrorCode.PARSE_FAILED: "Не удалось разобрать страницу вакансии",
    ErrorCode.PROVIDER_UNAVAILABLE: "Провайдер модели недоступен",
    ErrorCode.PROVIDER_TIMEOUT: "Провайдер модели не ответил вовремя",
    ErrorCode.INVALID_LLM_RESPONSE: "Модель вернула невалидный ответ",
    ErrorCode.FACT_CHECK_FAILED: "Проверка фактов не пройдена",
    ErrorCode.APPLY_FORM_UNKNOWN: "Форма отклика не распознана",
    ErrorCode.APPLICATION_STATE_UNKNOWN: "Состояние отклика неизвестно",
    ErrorCode.LIMIT_REACHED: "Достигнут лимит откликов",
    ErrorCode.PERSONAL_DATA_REQUESTED: "Запрошены личные данные",
}


class RunStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"
    INTERRUPTED = "INTERRUPTED"


RUN_STATUS_LABELS: dict[str, str] = {
    RunStatus.IDLE: "Не запущен",
    RunStatus.RUNNING: "Работает",
    RunStatus.PAUSED: "Пауза",
    RunStatus.STOPPED: "Остановлен",
    RunStatus.FINISHED: "Завершён",
    RunStatus.INTERRUPTED: "Прерван",
}


class StopReason(StrEnum):
    USER = "USER"
    FINISHED = "FINISHED"
    TOO_MANY_ERRORS = "TOO_MANY_ERRORS"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    LIMIT_REACHED = "LIMIT_REACHED"
    NEEDS_USER_ACTION = "NEEDS_USER_ACTION"


STOP_REASON_LABELS: dict[str, str] = {
    StopReason.USER: "Остановлен пользователем",
    StopReason.FINISHED: "Все задачи выполнены",
    StopReason.TOO_MANY_ERRORS: "5 ошибок подряд",
    StopReason.PROVIDER_UNAVAILABLE: "Провайдер модели недоступен",
    StopReason.LIMIT_REACHED: "Достигнут лимит откликов",
    StopReason.NEEDS_USER_ACTION: "Требуется действие пользователя",
}


class JobType(StrEnum):
    SEARCH = "SEARCH"
    FETCH_VACANCY = "FETCH_VACANCY"
    FILTER = "FILTER"
    ANALYZE = "ANALYZE"
    GENERATE_LETTER = "GENERATE_LETTER"
    FACT_CHECK = "FACT_CHECK"
    APPLY = "APPLY"
    SYNC_STATUS = "SYNC_STATUS"


class JobState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class BotMode(StrEnum):
    """Насколько бот самостоятелен (§20, ось 1)."""

    MANUAL = "MANUAL"
    SEMI_AUTO = "SEMI_AUTO"
    AUTO = "AUTO"


BOT_MODE_LABELS: dict[str, str] = {
    BotMode.MANUAL: "Ручной",
    BotMode.SEMI_AUTO: "Полуавтомат",
    BotMode.AUTO: "Автомат",
}


class RuntimeMode(StrEnum):
    """Доходит ли дело до реальной отправки (§20, ось 2)."""

    DRY_RUN = "DRY_RUN"
    LIVE = "LIVE"


RUNTIME_MODE_LABELS: dict[str, str] = {
    RuntimeMode.DRY_RUN: "Без отправки",
    RuntimeMode.LIVE: "Боевой",
}


class RemoteMode(StrEnum):
    REMOTE_ONLY = "REMOTE_ONLY"
    REMOTE_OR_HYBRID = "REMOTE_OR_HYBRID"
    ANY = "ANY"


REMOTE_MODE_LABELS: dict[str, str] = {
    RemoteMode.REMOTE_ONLY: "Только удалённо",
    RemoteMode.REMOTE_OR_HYBRID: "Удалённо или гибрид",
    RemoteMode.ANY: "Любой",
}


class WorkFormat(StrEnum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    OFFICE = "OFFICE"
    UNKNOWN = "UNKNOWN"


WORK_FORMAT_LABELS: dict[str, str] = {
    WorkFormat.REMOTE: "Удалённо",
    WorkFormat.HYBRID: "Гибрид",
    WorkFormat.OFFICE: "Офис",
    WorkFormat.UNKNOWN: "Не указан",
}


class MatchType(StrEnum):
    CONTAINS = "CONTAINS"
    EQUALS = "EQUALS"


class CompanyRuleAction(StrEnum):
    SKIP = "SKIP"
    ALWAYS_REVIEW = "ALWAYS_REVIEW"
    BOOST = "BOOST"
    PENALTY = "PENALTY"


COMPANY_RULE_ACTION_LABELS: dict[str, str] = {
    CompanyRuleAction.SKIP: "Пропустить",
    CompanyRuleAction.ALWAYS_REVIEW: "Всегда на проверку",
    CompanyRuleAction.BOOST: "Повысить приоритет",
    CompanyRuleAction.PENALTY: "Штраф к скору",
}


class LetterSource(StrEnum):
    AI = "AI"
    MANUAL = "MANUAL"
    AI_EDITED = "AI_EDITED"
    AI_REWRITE = "AI_REWRITE"


LETTER_SOURCE_LABELS: dict[str, str] = {
    LetterSource.AI: "Сгенерировано",
    LetterSource.MANUAL: "Написано вручную",
    LetterSource.AI_EDITED: "Сгенерировано и отредактировано",
    LetterSource.AI_REWRITE: "Перегенерировано",
}


class ProviderType(StrEnum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    CLI = "cli"


class PromptKey(StrEnum):
    RESUME_DIGEST = "resume_digest"
    ANALYZE = "analyze"
    LETTER = "letter"
    FACT_CHECK = "fact_check"
    ANSWER_QUESTION = "answer_question"
    SUSPICIOUS_RULES = "suspicious_rules"


PROMPT_KEY_LABELS: dict[str, str] = {
    PromptKey.RESUME_DIGEST: "Выжимка резюме",
    PromptKey.ANALYZE: "Анализ вакансии",
    PromptKey.LETTER: "Сопроводительное письмо",
    PromptKey.FACT_CHECK: "Проверка фактов",
    PromptKey.ANSWER_QUESTION: "Ответы на вопросы",
    PromptKey.SUSPICIOUS_RULES: "Правила подозрительности",
}


class EventLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
