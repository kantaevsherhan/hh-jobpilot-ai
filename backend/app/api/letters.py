"""Письма: ручное написание, генерация, перегенерация, выбор версии (§17)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Session
from app.api.vacancies import LetterOut
from app.core.enums import LetterSource, VacancyStatus
from app.core.errors import ConflictError
from app.llm.steps.fact_check import dictionary_check, fact_check, find_placeholders
from app.llm.steps.letter import check_instructions_followed, pick_language, write_letter
from app.storage.models import Letter, LetterExample, Resume, Vacancy
from app.storage.repositories import crud
from app.storage.repositories import settings as settings_repo
from app.storage.repositories import vacancies as repo

router = APIRouter(tags=["Письма"])


async def _next_version(session: Session, decision_id: int) -> int:
    rows = list(
        (await session.scalars(select(Letter).where(Letter.resume_vacancy_id == decision_id))).all()
    )
    for row in rows:
        row.is_selected = False
    return len(rows) + 1


class ManualLetter(BaseModel):
    resume_id: int
    content: str = Field(min_length=1)
    language: str = "ru"


@router.post(
    "/vacancies/{vacancy_id}/letters/manual",
    response_model=LetterOut,
    summary="Написать письмо самому",
)
async def manual_letter(vacancy_id: int, payload: ManualLetter, session: Session) -> Letter:
    decision = await repo.ensure_decision(session, payload.resume_id, vacancy_id)
    letter = Letter(
        resume_vacancy_id=decision.id,
        version=await _next_version(session, decision.id),
        source=LetterSource.MANUAL.value,
        language=payload.language,
        content=payload.content,
        char_count=len(payload.content),
        is_selected=True,
        # Написанное человеком проверять на выдумки незачем
        fact_check_passed=True,
    )
    session.add(letter)
    await repo.ensure_decision(
        session, payload.resume_id, vacancy_id, status=VacancyStatus.LETTER_READY.value
    )
    await session.commit()
    await session.refresh(letter)
    return letter


class GenerateRequest(BaseModel):
    resume_id: int
    instruction: str | None = None


@router.post(
    "/vacancies/{vacancy_id}/letters/generate",
    response_model=LetterOut,
    summary="Сгенерировать письмо",
)
async def generate_letter(vacancy_id: int, payload: GenerateRequest, session: Session) -> Letter:
    resume = await crud.get_or_404(session, Resume, payload.resume_id, "Резюме")
    vacancy = await crud.get_or_404(session, Vacancy, vacancy_id, "Вакансия")
    decision = await repo.ensure_decision(session, resume.id, vacancy_id)

    analysis: dict[str, Any] = (decision.analysis_json or {}).get("parsed", {})
    app_settings = await settings_repo.get_all(session)
    llm_settings = app_settings.get("llm", {})

    examples = list(
        (
            await session.scalars(
                select(LetterExample)
                .where(
                    LetterExample.is_active,
                    (LetterExample.resume_id.is_(None)) | (LetterExample.resume_id == resume.id),
                )
                # В промпт идут первые три: предпочтительные должны попасть туда точно
                .order_by(LetterExample.is_preferred.desc(), LetterExample.id)
            )
        ).all()
    )
    hidden = list(decision.hidden_instructions)

    generated, _ = await write_letter(
        session,
        digest=resume.digest_json,
        resume_text=resume.raw_text,
        allowed_facts=resume.allowed_facts,
        title=vacancy.title,
        company_name=vacancy.company_name,
        description=vacancy.description,
        matched_skills=list(analysis.get("matched_skills", [])),
        green_flags=list(analysis.get("green_flags", [])),
        hidden_instructions=hidden,
        language=pick_language(vacancy.description_lang, list(resume.letter_languages)),
        examples=[example.content for example in examples],
        min_chars=int(llm_settings.get("letter_min_chars", 400)),
        max_chars=int(llm_settings.get("letter_max_chars", 800)),
        max_vacancy_chars=int(llm_settings.get("max_vacancy_chars", 6000)),
        extra_instruction=payload.instruction,
    )

    missing = check_instructions_followed(generated.letter, hidden)
    unsupported = dictionary_check(
        generated.letter,
        resume_text=resume.raw_text,
        allowed_facts=resume.allowed_facts,
        resume_skills=[skill.name for skill in resume.skills],
    )

    letter = Letter(
        resume_vacancy_id=decision.id,
        version=await _next_version(session, decision.id),
        source=LetterSource.AI_REWRITE.value if payload.instruction else LetterSource.AI.value,
        language=generated.language,
        content=generated.letter,
        char_count=len(generated.letter),
        is_selected=True,
        fact_check_json={
            "dictionary_unsupported": unsupported,
            "instructions_missing": missing,
        },
        fact_check_passed=None,
    )
    session.add(letter)
    await session.commit()
    await session.refresh(letter)
    return letter


class RewriteRequest(BaseModel):
    instruction: str = Field(min_length=1)


@router.post(
    "/letters/{letter_id}/select", response_model=LetterOut, summary="Выбрать версию письма"
)
async def select_letter(letter_id: int, session: Session) -> Letter:
    letter = await crud.get_or_404(session, Letter, letter_id, "Письмо")
    siblings = list(
        (
            await session.scalars(
                select(Letter).where(Letter.resume_vacancy_id == letter.resume_vacancy_id)
            )
        ).all()
    )
    for row in siblings:
        row.is_selected = row.id == letter.id
    await session.commit()
    await session.refresh(letter)
    return letter


@router.post("/letters/{letter_id}/fact-check", response_model=LetterOut, summary="Проверить факты")
async def run_fact_check(letter_id: int, resume_id: int, session: Session) -> Letter:
    letter = await crud.get_or_404(session, Letter, letter_id, "Письмо")
    resume = await crud.get_or_404(session, Resume, resume_id, "Резюме")

    unsupported = dictionary_check(
        letter.content,
        resume_text=resume.raw_text,
        allowed_facts=resume.allowed_facts,
        resume_skills=[skill.name for skill in resume.skills],
    )
    check, _ = await fact_check(
        session,
        letter=letter.content,
        digest=resume.digest_json,
        resume_text=resume.raw_text,
        allowed_facts=resume.allowed_facts,
    )
    placeholders = find_placeholders(letter.content)

    # instructions_missing из генерации сохраняется: проверка фактов его не пересчитывает
    letter.fact_check_json = {
        **(letter.fact_check_json or {}),
        "dictionary_unsupported": unsupported,
        "placeholders": placeholders,
        "llm": check.model_dump(),
    }
    letter.fact_check_passed = check.valid and not unsupported and not placeholders
    await session.commit()
    await session.refresh(letter)
    return letter


@router.delete("/letters/{letter_id}", status_code=204, summary="Удалить версию письма")
async def delete_letter(letter_id: int, session: Session) -> None:
    letter = await crud.get_or_404(session, Letter, letter_id, "Письмо")
    if letter.is_selected:
        raise ConflictError(
            "LETTER_SELECTED", "Нельзя удалить выбранную версию — сначала выберите другую"
        )
    await crud.remove(session, letter)
