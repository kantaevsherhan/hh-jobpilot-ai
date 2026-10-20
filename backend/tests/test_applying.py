"""Идемпотентность отклика и лимиты (§20, §21, §30)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RuntimeMode, VacancyStatus
from app.pipeline.applying import applications_today, check_can_apply, record_application
from app.storage.models import Vacancy
from tests.factories import make_resume, make_vacancy

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


async def setup_pair(session: AsyncSession) -> tuple[int, int]:
    resume, vacancy = make_resume(), make_vacancy()
    session.add_all([resume, vacancy])
    await session.commit()
    return resume.id, vacancy.id


async def test_первый_отклик_разрешён(session: AsyncSession) -> None:
    _, vacancy_id = await setup_pair(session)

    guard = await check_can_apply(
        session, vacancy_id=vacancy_id, runtime_mode=RuntimeMode.LIVE, now=NOW
    )

    assert guard.allowed is True


async def test_второй_отклик_не_проходит(session: AsyncSession) -> None:
    resume_id, vacancy_id = await setup_pair(session)
    await record_application(session, vacancy_id=vacancy_id, resume_id=resume_id)

    guard = await check_can_apply(
        session, vacancy_id=vacancy_id, runtime_mode=RuntimeMode.LIVE, now=NOW
    )

    assert guard.allowed is False
    assert guard.error_code == "DUPLICATE"
    assert guard.status == VacancyStatus.APPLIED


async def test_отклик_с_другого_резюме_тоже_не_проходит(session: AsyncSession) -> None:
    resume_id, vacancy_id = await setup_pair(session)
    other = make_resume(name="Go")
    session.add(other)
    await session.commit()
    await record_application(session, vacancy_id=vacancy_id, resume_id=resume_id)

    guard = await check_can_apply(
        session, vacancy_id=vacancy_id, runtime_mode=RuntimeMode.LIVE, now=NOW
    )

    assert guard.allowed is False


async def test_dry_run_доходит_до_формы_но_не_отправляет(session: AsyncSession) -> None:
    _, vacancy_id = await setup_pair(session)

    guard = await check_can_apply(
        session, vacancy_id=vacancy_id, runtime_mode=RuntimeMode.DRY_RUN, now=NOW
    )

    assert guard.allowed is False
    assert guard.status == VacancyStatus.APPLY_PREPARED


async def test_закрытая_вакансия_не_отправляется(session: AsyncSession) -> None:
    resume, vacancy = make_resume(), make_vacancy(is_closed=True)
    session.add_all([resume, vacancy])
    await session.commit()

    guard = await check_can_apply(
        session, vacancy_id=vacancy.id, runtime_mode=RuntimeMode.LIVE, now=NOW
    )

    assert guard.allowed is False
    assert guard.status == VacancyStatus.VACANCY_CLOSED


async def test_проваленный_факт_чек_блокирует_отправку(session: AsyncSession) -> None:
    _, vacancy_id = await setup_pair(session)

    guard = await check_can_apply(
        session,
        vacancy_id=vacancy_id,
        runtime_mode=RuntimeMode.LIVE,
        fact_check_passed=False,
        now=NOW,
    )

    assert guard.allowed is False
    assert guard.error_code == "FACT_CHECK_FAILED"


async def test_лимит_за_прогон(session: AsyncSession) -> None:
    _, vacancy_id = await setup_pair(session)

    guard = await check_can_apply(
        session,
        vacancy_id=vacancy_id,
        runtime_mode=RuntimeMode.LIVE,
        applications_in_run=20,
        max_per_run=20,
        now=NOW,
    )

    assert guard.allowed is False
    assert guard.error_code == "LIMIT_REACHED"


async def test_дневной_лимит_считается_по_календарным_суткам(session: AsyncSession) -> None:
    resume = make_resume()
    session.add(resume)
    await session.flush()
    for index in range(3):
        vacancy = Vacancy(hh_id=str(index), url=f"https://hh.kz/vacancy/{index}", title="V")
        session.add(vacancy)
        await session.flush()
        await record_application(session, vacancy_id=vacancy.id, resume_id=resume.id)

    # Отклик позавчера в счёт сегодняшнего дня не идёт
    old = Vacancy(hh_id="old", url="https://hh.kz/vacancy/old", title="V")
    session.add(old)
    await session.flush()
    application = await record_application(session, vacancy_id=old.id, resume_id=resume.id)
    application.applied_at = NOW - timedelta(days=2)
    await session.commit()

    assert await applications_today(session, NOW) == 3


async def test_дневной_лимит_останавливает_отправку(session: AsyncSession) -> None:
    resume_id, vacancy_id = await setup_pair(session)
    other = Vacancy(hh_id="777", url="https://hh.kz/vacancy/777", title="V")
    session.add(other)
    await session.flush()
    await record_application(session, vacancy_id=other.id, resume_id=resume_id)

    guard = await check_can_apply(
        session,
        vacancy_id=vacancy_id,
        runtime_mode=RuntimeMode.LIVE,
        max_per_day=1,
        now=NOW,
    )

    assert guard.allowed is False
    assert guard.error_code == "LIMIT_REACHED"


def test_длинное_письмо_успевает_напечататься() -> None:
    from app.browser.apply import typing_timeout_ms

    # 800 символов по 40 мс — это 32 секунды, стандартные 30 с Playwright не хватало
    assert typing_timeout_ms(800, 40) > 800 * 40


def test_письмо_в_поле_сверяется_с_исходным() -> None:
    from app.browser.apply import letters_match

    assert letters_match("Здравствуйте!\n\nТекст", "Здравствуйте!\r\n\r\nТекст ")
    # Черновик HH, к которому допечатали письмо, — это несовпадение, отправлять нельзя
    assert not letters_match("Здравствуйте!", "Старый черновикЗдравствуйте!")


class _NoDelays:
    """Задержки в тестах не ждут."""

    def seconds(self, _key: str) -> float:
        return 0.0

    async def pause(self, _key: str) -> float:
        return 0.0


def _patch_page(
    monkeypatch, form, *, letter_error: Exception | None = None, letter_ok: bool = True
):
    from app.browser import apply as apply_page

    calls: list[str] = []

    async def open_form(_page):
        calls.append("open_form")
        return form

    async def dismiss_dialogs(_page):
        calls.append("dismiss")

    async def type_letter(_page, _letter, _delay):
        calls.append("type")
        if letter_error:
            raise letter_error

    async def send_letter_after_apply(_page):
        calls.append("send_letter")
        return letter_ok

    async def submit(_page):
        calls.append("submit")
        return True

    for name, fn in {
        "open_form": open_form,
        "dismiss_dialogs": dismiss_dialogs,
        "type_letter": type_letter,
        "send_letter_after_apply": send_letter_after_apply,
        "submit": submit,
    }.items():
        monkeypatch.setattr(apply_page, name, fn)
    return calls


async def test_быстрый_отклик_засчитан_даже_если_письмо_упало(monkeypatch) -> None:
    from app.browser.apply import ApplyForm
    from app.core.enums import ErrorCode
    from app.pipeline.applying import send_application

    calls = _patch_page(
        monkeypatch, ApplyForm(can_apply=True, sent_on_click=True), letter_error=TimeoutError()
    )

    result = await send_application(None, "1", "Здравствуйте!", delays=_NoDelays())

    # Резюме уже ушло — отклик должен записаться, иначе возможен второй отклик
    assert result.sent is True
    assert result.error_code == ErrorCode.LETTER_NOT_SENT
    assert "submit" not in calls


async def test_быстрый_отклик_досылает_письмо(monkeypatch) -> None:
    from app.browser.apply import ApplyForm
    from app.pipeline.applying import send_application

    calls = _patch_page(monkeypatch, ApplyForm(can_apply=True, sent_on_click=True))

    result = await send_application(None, "1", "Здравствуйте!", delays=_NoDelays())

    assert result.sent is True
    assert result.letter_sent is True
    assert calls == ["open_form", "dismiss", "type", "send_letter"]


async def test_форма_с_вопросами_не_отправляется(monkeypatch) -> None:
    from app.browser.apply import ApplyForm
    from app.pipeline.applying import send_application

    calls = _patch_page(monkeypatch, ApplyForm(can_apply=True, questions=["Ваша зарплата?"]))

    result = await send_application(None, "1", "Здравствуйте!", delays=_NoDelays())

    assert result.sent is False
    assert result.needs_data is True
    assert "submit" not in calls


async def test_дослать_письмо_без_отклика_нельзя(client, session: AsyncSession) -> None:
    resume_id, vacancy_id = await setup_pair(session)

    response = await client.post(
        f"/api/v1/vacancies/{vacancy_id}/send-letter",
        json={"resume_id": resume_id, "letter_id": 1},
    )

    assert response.status_code == 409
