"""Шаги пайплайна: что происходит по каждому типу задачи (§22).

Единственный слой, который знает обо всех остальных: браузере, фильтрах,
моделях и хранилище (§4).
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.browser import search as search_page
from app.browser import vacancy as vacancy_page
from app.browser.manager import browser
from app.core.enums import (
    BotMode,
    EventLevel,
    JobType,
    LetterSource,
    SkipReason,
    VacancyStatus,
)
from app.core.errors import AppError
from app.core.logging import get_logger
from app.filters.engine import VacancyFacts, run_filters
from app.filters.suspicious import check_suspicious
from app.llm import embellishment
from app.llm.steps.analyze import analyze_vacancy
from app.llm.steps.fact_check import (
    dictionary_blocks,
    dictionary_check,
    fact_check,
    find_placeholders,
)
from app.llm.steps.letter import check_instructions_followed, pick_language, write_letter
from app.pipeline import applying, events, queue
from app.pipeline.context import RunContext
from app.pipeline.decision import DecisionInput, decide
from app.storage.models import Letter, LetterExample, Run, SearchProfile, Vacancy
from app.storage.models.base import utcnow
from app.storage.repositories import vacancies as vacancy_repo

log = get_logger(__name__)

# Дальше 10-й страницы HH выдаёт то, что подходит всё хуже; лимит профиля обычно
# набирается раньше
MAX_SEARCH_PAGES = 10


async def run_search(
    session: AsyncSession, run: Run, ctx: RunContext, payload: dict[str, Any]
) -> None:
    """Собрать выдачу и поставить в очередь только новые выжившие вакансии (§10)."""
    profile = await session.get_one(SearchProfile, int(payload["search_profile_id"]))
    page = await browser.page()
    rules = ctx.rules_for(profile)

    queued = 0
    limit = profile.max_vacancies_per_run

    filters: dict[str, Any] = {
        "areas": [str(a) for a in profile.areas],
        "experience": [str(e) for e in profile.experience_levels],
        "remote_mode": profile.remote_mode,
        "max_age_days": profile.max_age_days,
    }
    targets: list[tuple[str, dict[str, Any]]] = [
        (f"«{query.text}»", {"query": query.text, **filters}) for query in profile.queries
    ]
    if profile.use_recommendations:
        resume_hash = ctx.resume.hh_resume_id or search_page.resume_hash_from_url(
            ctx.resume.hh_resume_url
        )
        if resume_hash:
            # Рекомендации первыми: HH уже отобрал их под резюме
            targets.insert(
                0,
                ("Рекомендации HH «Для вас»", {"query": "", "resume_hash": resume_hash, **filters}),
            )
        else:
            await events.log_event(
                session,
                run.id,
                "search_skipped",
                "Рекомендации HH пропущены: в резюме нет ссылки на hh.kz",
                level=EventLevel.WARNING,
            )

    # Страницы выдачи: первая часто целиком из уже знакомых вакансий, а лента
    # «Для вас» — это сотни вакансий. Обход идёт, пока не набран лимит профиля
    pages = [
        (label, params, number) for label, params in targets for number in range(MAX_SEARCH_PAGES)
    ]
    exhausted: set[str] = set()

    for label, params, page_number in pages:
        if queued >= limit:
            break
        if label in exhausted:
            continue

        url = search_page.build_url(**params, page=page_number)
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        await ctx.delays.pause("page_load")

        items = await search_page.collect_page(page)
        await events.log_event(
            session,
            run.id,
            "search",
            f"{label}, стр. {page_number + 1}: найдено {len(items)}",
            payload={"url": url},
        )
        _bump(run, "found", len(items))
        if not items:
            exhausted.add(label)
            continue

        known = await vacancy_repo.known_hh_ids(session, [item.hh_id for item in items])

        for item in items:
            if queued >= limit:
                break

            if item.hh_id in known:
                await vacancy_repo.touch(session, item.hh_id)
                continue

            # Отсев по тому, что видно прямо в выдаче — карточку не открываем
            verdict = run_filters(
                VacancyFacts(title=item.title, company_name=item.company_name),
                rules,
                ctx.company_rules,
            )
            vacancy, _ = await vacancy_repo.save_from_search(session, item)
            _bump(run, "new", 1)

            if not verdict.passed:
                await vacancy_repo.ensure_decision(
                    session,
                    ctx.resume.id,
                    vacancy.id,
                    status=VacancyStatus.FILTERED_OUT.value,
                    skip_reason=verdict.reason.value if verdict.reason else None,
                    skip_details=verdict.details,
                    decided_at=utcnow(),
                )
                _bump(run, "filtered", 1)
                continue

            await queue.add(
                session,
                run.id,
                JobType.FETCH_VACANCY,
                {"vacancy_id": vacancy.id, "search_profile_id": profile.id},
            )
            queued += 1

        await ctx.delays.pause("between_search_pages")

    await session.commit()


async def fetch_vacancy(
    session: AsyncSession, run: Run, ctx: RunContext, payload: dict[str, Any]
) -> None:
    """Открыть карточку, дочитать поля и прогнать полные фильтры."""
    vacancy_id = int(payload["vacancy_id"])
    vacancy = await session.get_one(Vacancy, vacancy_id)
    profile = await session.get_one(SearchProfile, int(payload["search_profile_id"]))

    page = await browser.page()
    data = await vacancy_page.open_and_extract(page, vacancy.hh_id)
    await ctx.delays.pause("page_load")

    saved, _ = await vacancy_repo.save_from_card(session, data)

    verdict = run_filters(
        VacancyFacts(
            title=saved.title,
            description=saved.description,
            company_name=saved.company_name,
            salary_from=saved.salary_from,
            salary_to=saved.salary_to,
            currency=saved.currency,
            salary_gross=saved.salary_gross,
            work_format=saved.work_format,
            experience=saved.experience,
            published_at=saved.published_at,
        ),
        ctx.rules_for(profile),
        ctx.company_rules,
    )

    if not verdict.passed:
        await vacancy_repo.ensure_decision(
            session,
            ctx.resume.id,
            saved.id,
            status=VacancyStatus.FILTERED_OUT.value,
            skip_reason=verdict.reason.value if verdict.reason else None,
            skip_details=verdict.details,
            decided_at=utcnow(),
        )
        _bump(run, "filtered", 1)
        await session.commit()
        return

    await vacancy_repo.ensure_decision(
        session, ctx.resume.id, saved.id, status=VacancyStatus.DISCOVERED.value
    )
    await queue.add(
        session,
        run.id,
        JobType.ANALYZE,
        {
            "vacancy_id": saved.id,
            "score_delta": verdict.score_delta,
            "force_review": verdict.force_review,
        },
    )


async def analyze(
    session: AsyncSession, run: Run, ctx: RunContext, payload: dict[str, Any]
) -> None:
    """Один LLM-вызов, затем решение чистой функцией (§15)."""
    vacancy_id = int(payload["vacancy_id"])
    vacancy = await _any_vacancy(session, vacancy_id)
    decision_row = await vacancy_repo.ensure_decision(
        session, ctx.resume.id, vacancy_id, status=VacancyStatus.ANALYZING.value
    )

    hard_suspicious = check_suspicious(
        title=vacancy.title,
        description=vacancy.description,
        company_name=vacancy.company_name,
    )

    try:
        analysis, result = await analyze_vacancy(
            session,
            digest=ctx.resume.digest_json,
            allowed_facts=ctx.resume.allowed_facts,
            title=vacancy.title,
            company_name=vacancy.company_name,
            description=vacancy.description,
            max_vacancy_chars=int(ctx.llm_settings.get("max_vacancy_chars", 6000)),
        )
    except AppError as exc:
        if exc.error_code == "INVALID_LLM_RESPONSE":
            await vacancy_repo.ensure_decision(
                session,
                ctx.resume.id,
                vacancy_id,
                status=VacancyStatus.ANALYSIS_FAILED.value,
                skip_details=exc.human_message,
                analysis_json={"error": exc.technical_details},
            )
            await events.log_event(
                session,
                run.id,
                "analysis_failed",
                f"{vacancy.title}: {exc.human_message}",
                level=EventLevel.ERROR,
                resume_vacancy_id=decision_row.id,
            )
            _bump(run, "errors", 1)
            return
        raise

    verdict = decide(
        DecisionInput(
            analysis=analysis,
            min_score=ctx.resume.min_score,
            auto_apply_score=ctx.resume.auto_apply_score,
            company_score_delta=int(payload.get("score_delta", 0)),
            force_review=bool(payload.get("force_review", False)),
            hard_suspicious_reasons=tuple(hard_suspicious),
            mode=run.mode,
            answer_employer_questions=bool(
                ctx.settings.get("bot", {}).get("answer_employer_questions", False)
            ),
            already_applied=await vacancy_repo.has_application(session, vacancy_id),
            broad=ctx.settings.get("bot", {}).get("apply_breadth", "broad") == "broad",
        )
    )

    await vacancy_repo.ensure_decision(
        session,
        ctx.resume.id,
        vacancy_id,
        status=verdict.status.value,
        skip_reason=verdict.skip_reason.value if verdict.skip_reason else None,
        skip_details=verdict.skip_details,
        score=verdict.score,
        analysis_json={"parsed": analysis.model_dump(), "raw": result.raw},
        is_suspicious=verdict.status == VacancyStatus.SUSPICIOUS,
        suspicious_reasons=list(verdict.suspicious_reasons),
        hidden_instructions=analysis.hidden_instructions,
        decided_at=utcnow(),
    )

    _bump(run, "analyzed", 1)
    if verdict.status == VacancyStatus.SUSPICIOUS:
        _bump(run, "suspicious", 1)
    elif verdict.status in (VacancyStatus.REVIEW_REQUIRED, VacancyStatus.RECOMMENDED):
        _bump(run, "review", 1)
        _bump(run, "suitable", 1)

    await events.log_event(
        session,
        run.id,
        "analyzed",
        f"{vacancy.title}: {verdict.status.value}, оценка {verdict.score}",
        resume_vacancy_id=decision_row.id,
        payload={"score": verdict.score, "reason": analysis.reason},
    )

    if verdict.status == VacancyStatus.LETTER_READY:
        _bump(run, "suitable", 1)
        await queue.add(session, run.id, JobType.GENERATE_LETTER, {"vacancy_id": vacancy_id})

    await ctx.delays.pause("between_vacancies")


async def generate_letter(
    session: AsyncSession, run: Run, ctx: RunContext, payload: dict[str, Any]
) -> None:
    """Письмо под конкретную вакансию плюс проверка скрытых инструкций (§16, §17)."""
    vacancy_id = int(payload["vacancy_id"])
    vacancy = await _any_vacancy(session, vacancy_id)
    decision_row = await vacancy_repo.ensure_decision(session, ctx.resume.id, vacancy_id)
    analysis = (decision_row.analysis_json or {}).get("parsed", {})

    letter, _ = await _write_with_instruction_retry(
        session,
        ctx,
        vacancy=vacancy,
        analysis=analysis,
        hidden=list(decision_row.hidden_instructions),
    )

    unsupported = dictionary_check(
        letter.letter,
        resume_text=ctx.resume.raw_text,
        allowed_facts=ctx.resume.allowed_facts,
        resume_skills=[skill.name for skill in ctx.resume.skills],
    )

    version = 1 + len(
        list(
            (
                await session.scalars(
                    select(Letter).where(Letter.resume_vacancy_id == decision_row.id)
                )
            ).all()
        )
    )
    row = Letter(
        resume_vacancy_id=decision_row.id,
        version=version,
        source=LetterSource.AI.value,
        language=letter.language,
        content=letter.letter,
        char_count=len(letter.letter),
        is_selected=True,
        fact_check_json={"dictionary_unsupported": unsupported} if unsupported else None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    await events.log_event(
        session,
        run.id,
        "letter",
        f"{vacancy.title}: письмо на {len(letter.letter)} символов",
        resume_vacancy_id=decision_row.id,
    )

    await queue.add(
        session, run.id, JobType.FACT_CHECK, {"vacancy_id": vacancy_id, "letter_id": row.id}
    )


async def run_fact_check(
    session: AsyncSession, run: Run, ctx: RunContext, payload: dict[str, Any]
) -> None:
    """Словарная проверка уже прошла при генерации, здесь — модель (§18)."""
    letter_row = await session.get_one(Letter, int(payload["letter_id"]))
    vacancy_id = int(payload["vacancy_id"])
    decision_row = await vacancy_repo.ensure_decision(session, ctx.resume.id, vacancy_id)

    dictionary_unsupported = (letter_row.fact_check_json or {}).get("dictionary_unsupported", [])

    check, _ = await fact_check(
        session,
        letter=letter_row.content,
        digest=ctx.resume.digest_json,
        resume_text=ctx.resume.raw_text,
        allowed_facts=ctx.resume.allowed_facts,
    )
    placeholders = find_placeholders(letter_row.content)

    level = await embellishment.current_level(session)
    passed = (
        check.valid
        and not (dictionary_unsupported and dictionary_blocks(level))
        and not placeholders
    )
    letter_row.fact_check_json = {
        **(letter_row.fact_check_json or {}),
        "dictionary_unsupported": dictionary_unsupported,
        "placeholders": placeholders,
        "llm": check.model_dump(),
    }
    letter_row.fact_check_passed = passed
    await session.commit()

    if not passed:
        await vacancy_repo.ensure_decision(
            session,
            ctx.resume.id,
            vacancy_id,
            status=VacancyStatus.REVIEW_REQUIRED.value,
            skip_details="Проверка фактов не пройдена: "
            + "; ".join([*dictionary_unsupported, *check.unsupported_claims]),
        )
        await events.log_event(
            session,
            run.id,
            "fact_check_failed",
            "Письмо не прошло проверку фактов, отправка заблокирована",
            level=EventLevel.WARNING,
            resume_vacancy_id=decision_row.id,
        )
        _bump(run, "review", 1)
        return

    await vacancy_repo.ensure_decision(
        session, ctx.resume.id, vacancy_id, status=VacancyStatus.LETTER_READY.value
    )

    if run.mode == BotMode.AUTO:
        await queue.add(
            session, run.id, JobType.APPLY, {"vacancy_id": vacancy_id, "letter_id": letter_row.id}
        )
    else:
        _bump(run, "review", 1)


async def apply(session: AsyncSession, run: Run, ctx: RunContext, payload: dict[str, Any]) -> None:
    """Отправка отклика со всеми проверками §21."""
    from app.browser import apply as apply_page

    vacancy_id = int(payload["vacancy_id"])
    letter_id = payload.get("letter_id")
    vacancy = await _any_vacancy(session, vacancy_id)
    decision_row = await vacancy_repo.ensure_decision(session, ctx.resume.id, vacancy_id)
    letter_row = await session.get(Letter, int(letter_id)) if letter_id else None

    limits = ctx.limits
    guard = await applying.check_can_apply(
        session,
        vacancy_id=vacancy_id,
        runtime_mode=run.runtime_mode,
        applications_in_run=int(run.counters_json.get("applied", 0)),
        max_per_run=int(limits.get("max_applications_per_run", 20)),
        max_per_day=int(limits.get("max_applications_per_day", 30)),
        fact_check_passed=letter_row.fact_check_passed if letter_row else None,
    )

    if not guard.allowed:
        if guard.status is not None:
            await vacancy_repo.ensure_decision(
                session, ctx.resume.id, vacancy_id, status=guard.status.value
            )
        await events.log_event(
            session,
            run.id,
            "apply_skipped",
            f"{vacancy.title}: {guard.message}",
            level=EventLevel.WARNING,
            resume_vacancy_id=decision_row.id,
        )
        if guard.error_code == "LIMIT_REACHED":
            raise AppError("LIMIT_REACHED", guard.message or "Лимит откликов исчерпан")
        return

    page = await browser.page()
    await page.goto(vacancy_page.vacancy_url(vacancy.hh_id), wait_until="domcontentloaded")
    await ctx.delays.pause("page_load")

    state = await apply_page.inspect(page, vacancy.hh_id)
    if state.already_applied:
        await applying.record_application(
            session,
            vacancy_id=vacancy_id,
            resume_id=ctx.resume.id,
            run_id=run.id,
            hh_status="SENT",
            error_code="ALREADY_APPLIED",
        )
        await vacancy_repo.ensure_decision(
            session,
            ctx.resume.id,
            vacancy_id,
            status=VacancyStatus.APPLIED.value,
            skip_reason=SkipReason.ALREADY_APPLIED.value,
        )
        return

    if state.is_external:
        await vacancy_repo.ensure_decision(
            session, ctx.resume.id, vacancy_id, status=VacancyStatus.EXTERNAL_APPLY.value
        )
        return

    # Нет своей кнопки отклика (архив, снята с публикации) — форму не открываем:
    # иначе под руку попадает кнопка чужой вакансии из блока рекомендаций
    if not state.can_apply:
        vacancy.is_closed = True
        await vacancy_repo.ensure_decision(
            session,
            ctx.resume.id,
            vacancy_id,
            status=VacancyStatus.VACANCY_CLOSED.value,
            skip_details=state.blocked_reason or "На странице нет кнопки отклика",
        )
        await session.commit()
        return

    await ctx.delays.pause("before_open_form")
    result = await applying.send_application(
        page, vacancy.hh_id, letter_row.content if letter_row else None, delays=ctx.delays
    )

    if result.needs_data:
        await vacancy_repo.ensure_decision(
            session,
            ctx.resume.id,
            vacancy_id,
            status=VacancyStatus.NEEDS_DATA.value,
            skip_details=result.detail,
        )
        return

    ok = bool(result.sent)
    await applying.record_application(
        session,
        vacancy_id=vacancy_id,
        resume_id=ctx.resume.id,
        letter_id=letter_row.id if letter_row else None,
        run_id=run.id,
        hh_status="SENT" if ok else None,
        error_code=result.error_code,
    )
    await vacancy_repo.ensure_decision(
        session,
        ctx.resume.id,
        vacancy_id,
        status=(VacancyStatus.APPLIED if ok else VacancyStatus.APPLY_UNKNOWN).value,
    )
    _bump(run, "applied", 1)

    await events.log_event(
        session,
        run.id,
        "applied" if ok else "apply_unknown",
        f"{vacancy.title}: {applying.result_message(result)}",
        level=EventLevel.INFO if ok else EventLevel.WARNING,
        resume_vacancy_id=decision_row.id,
    )
    await ctx.delays.pause("after_apply")


async def _write_with_instruction_retry(
    session: AsyncSession,
    ctx: RunContext,
    *,
    vacancy: Any,
    analysis: dict[str, Any],
    hidden: list[str],
) -> tuple[Any, list[str]]:
    """Одна повторная генерация, если скрытая инструкция не выполнена (§16)."""
    examples = list(
        (
            await session.scalars(
                select(LetterExample)
                .where(
                    LetterExample.is_active,
                    (LetterExample.resume_id.is_(None))
                    | (LetterExample.resume_id == ctx.resume.id),
                )
                # В промпт идут первые три: предпочтительные должны попасть туда точно
                .order_by(LetterExample.is_preferred.desc(), LetterExample.id)
            )
        ).all()
    )
    llm_settings = ctx.llm_settings

    async def generate(extra: str | None = None) -> Any:
        letter, _ = await write_letter(
            session,
            digest=ctx.resume.digest_json,
            resume_text=ctx.resume.raw_text,
            allowed_facts=ctx.resume.allowed_facts,
            title=vacancy.title,
            company_name=vacancy.company_name,
            description=vacancy.description,
            matched_skills=list(analysis.get("matched_skills", [])),
            green_flags=list(analysis.get("green_flags", [])),
            hidden_instructions=hidden,
            language=pick_language(vacancy.description_lang, list(ctx.resume.letter_languages)),
            examples=[example.content for example in examples],
            min_chars=int(llm_settings.get("letter_min_chars", 400)),
            max_chars=int(llm_settings.get("letter_max_chars", 800)),
            max_vacancy_chars=int(llm_settings.get("max_vacancy_chars", 6000)),
            extra_instruction=extra,
        )
        return letter

    letter = await generate()
    missing = check_instructions_followed(letter.letter, hidden)
    if missing:
        letter = await generate(
            "Обязательно включи в письмо дословно: " + ", ".join(f"«{word}»" for word in missing)
        )
        missing = check_instructions_followed(letter.letter, hidden)
    return letter, missing


async def _any_vacancy(session: AsyncSession, vacancy_id: int) -> Vacancy:
    return await session.get_one(Vacancy, vacancy_id)


def _bump(run: Run, key: str, amount: int = 1) -> None:
    counters = dict(run.counters_json or {})
    counters[key] = int(counters.get(key, 0)) + amount
    run.counters_json = counters


HANDLERS = {
    JobType.SEARCH.value: run_search,
    JobType.FETCH_VACANCY.value: fetch_vacancy,
    JobType.ANALYZE.value: analyze,
    JobType.GENERATE_LETTER.value: generate_letter,
    JobType.FACT_CHECK.value: run_fact_check,
    JobType.APPLY.value: apply,
}
