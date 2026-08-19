"""Схемы ответов модели. Каждый ответ валидируется, невалидный не сохраняется (§15)."""

from pydantic import BaseModel, ConfigDict, Field


class ResumeDigest(BaseModel):
    """Выжимка резюме (§7): ~600 токенов вместо 3500."""

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    years_total: float = 0
    level: str = ""
    core_stack: list[str] = Field(default_factory=list)
    additional: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    location: str = ""
    relocation: list[str] = Field(default_factory=list)
    work_formats: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profession: int = 0
    stack: int = 0
    experience: int = 0
    responsibilities: int = 0


class VacancyAnalysis(BaseModel):
    """Ответ шага анализа (§15).

    Зарплаты и формата работы тут нет намеренно: они уже проверены
    hard-фильтрами точно, спрашивать про них модель — давать ей соврать.
    """

    model_config = ConfigDict(extra="ignore")

    profession_match: bool
    can_do_job: bool
    score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    critical_missing: list[str] = Field(default_factory=list)

    red_flags: list[str] = Field(default_factory=list)
    green_flags: list[str] = Field(default_factory=list)

    is_suspicious: bool = False
    suspicious_reasons: list[str] = Field(default_factory=list)
    hidden_instructions: list[str] = Field(default_factory=list)
    employer_questions_detected: bool = False

    reason: str = ""


class LetterResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    letter: str
    language: str = "ru"


class FactCheckResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    valid: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)


class AnswerResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answer: str = ""
    answerable: bool = False
    reason: str = ""
