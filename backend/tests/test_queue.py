"""Очередь: остановка и возобновление не теряют и не дублируют задачи (§22, §30)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import JobState, JobType, RunStatus
from app.pipeline import queue
from app.storage.models import Job, Run
from tests.factories import make_resume


async def make_run(session: AsyncSession, status: str = RunStatus.RUNNING) -> Run:
    resume = make_resume()
    session.add(resume)
    await session.flush()
    run = Run(resume_id=resume.id, status=str(status))
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def test_задачи_берутся_по_очереди_и_не_дублируются(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add_many(session, run.id, JobType.ANALYZE, [{"n": 1}, {"n": 2}, {"n": 3}])

    taken = []
    while (job := await queue.take_next(session, run.id)) is not None:
        taken.append(job.payload_json["n"])
        await queue.finish(session, job, JobState.DONE)

    assert taken == [1, 2, 3]


async def test_взятая_задача_не_выдаётся_второй_раз(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add(session, run.id, JobType.ANALYZE, {"n": 1})

    first = await queue.take_next(session, run.id)
    second = await queue.take_next(session, run.id)

    assert first is not None
    assert second is None


async def test_остановка_и_возобновление_не_теряют_задачи(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add_many(session, run.id, JobType.ANALYZE, [{"n": i} for i in range(5)])

    # Обработали две и «остановились»
    for _ in range(2):
        job = await queue.take_next(session, run.id)
        assert job is not None
        await queue.finish(session, job, JobState.DONE)

    assert await queue.pending_count(session, run.id) == 3

    # Возобновились — ничего не переделываем заново
    resumed = []
    while (job := await queue.take_next(session, run.id)) is not None:
        resumed.append(job.payload_json["n"])
        await queue.finish(session, job, JobState.DONE)

    assert resumed == [2, 3, 4]
    assert await queue.pending_count(session, run.id) == 0


async def test_после_падения_прогон_помечается_прерванным(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add(session, run.id, JobType.ANALYZE, {"n": 1})
    job = await queue.take_next(session, run.id)
    assert job is not None

    report = await queue.recover_after_crash(session)

    await session.refresh(run)
    await session.refresh(job)
    assert run.status == RunStatus.INTERRUPTED
    assert job.state == JobState.PENDING
    assert report["jobs_requeued"] == 1


async def test_отклик_после_падения_не_возвращается_в_очередь(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add(session, run.id, JobType.APPLY, {"vacancy_id": 1})
    job = await queue.take_next(session, run.id)
    assert job is not None

    report = await queue.recover_after_crash(session)

    await session.refresh(job)
    # Состояние отправленного отклика неизвестно — повторять вслепую нельзя (§21)
    assert job.state == JobState.FAILED
    assert report["applies_unknown"] == 1


async def test_счётчики_по_состояниям(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add_many(session, run.id, JobType.ANALYZE, [{"n": 1}, {"n": 2}])
    job = await queue.take_next(session, run.id)
    assert job is not None
    await queue.finish(session, job, JobState.DONE)

    counts = await queue.counts(session, run.id)

    total = await session.scalar(select(func.count()).select_from(Job))
    assert total == 2
    assert counts[JobState.DONE] == 1
    assert counts[JobState.PENDING] == 1


async def test_продолжение_после_остановки_поднимает_воркер(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """После остановки по недоступному провайдеру «Продолжить» обязано
    возобновить прогон с той же вакансии, а не просто сменить статус (§14)."""
    from app.pipeline.runner import BotRunner

    run = await make_run(session, RunStatus.STOPPED)
    run.stop_reason = "PROVIDER_UNAVAILABLE"
    await session.commit()
    await queue.add(session, run.id, JobType.ANALYZE, {"vacancy_id": 1})

    runner = BotRunner()
    runner.run_id = run.id
    started: list[int] = []

    async def fake_loop(run_id: int, *_: object) -> None:
        started.append(run_id)

    monkeypatch.setattr(runner, "_loop", fake_loop)

    await runner.resume()
    if runner._task is not None:
        await runner._task

    await session.refresh(run)
    assert started == [run.id]
    assert run.status == RunStatus.RUNNING
    assert run.stop_reason is None


async def test_продолжать_нечего_если_очередь_пуста(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.errors import ConflictError
    from app.pipeline.runner import BotRunner

    run = await make_run(session, RunStatus.FINISHED)
    runner = BotRunner()
    runner.run_id = run.id

    with pytest.raises(ConflictError):
        await runner.resume()


async def test_продолжить_находит_прогон_после_перезапуска(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_id живёт в памяти процесса, а очередь — в БД. После перезапуска
    приложения продолжить всё равно должно быть можно (§22)."""
    from app.pipeline.runner import BotRunner

    run = await make_run(session, RunStatus.INTERRUPTED)
    await queue.add(session, run.id, JobType.ANALYZE, {"vacancy_id": 1})

    runner = BotRunner()
    assert runner.run_id is None  # как после перезапуска бэкенда

    started: list[int] = []

    async def fake_loop(run_id: int, *_: object) -> None:
        started.append(run_id)

    monkeypatch.setattr(runner, "_loop", fake_loop)
    await runner.resume()
    if runner._task is not None:
        await runner._task

    assert started == [run.id]
    assert runner.run_id == run.id


async def test_завершённый_прогон_не_считается_продолжаемым(session: AsyncSession) -> None:
    from app.core.errors import ConflictError
    from app.pipeline.runner import BotRunner

    run = await make_run(session, RunStatus.FINISHED)
    await queue.add(session, run.id, JobType.ANALYZE, {"vacancy_id": 1})

    with pytest.raises(ConflictError):
        await BotRunner().resume()


async def test_начатая_вакансия_доводится_до_отклика_раньше_новых(session: AsyncSession) -> None:
    run = await make_run(session)
    await queue.add_many(session, run.id, JobType.FETCH_VACANCY, [{"n": 1}, {"n": 2}])
    await queue.add(session, run.id, JobType.FACT_CHECK, {"n": 3})
    await queue.add(session, run.id, JobType.APPLY, {"n": 4})

    taken = []
    while (job := await queue.take_next(session, run.id)) is not None:
        taken.append(job.payload_json["n"])
        await queue.finish(session, job, JobState.DONE)

    # Отклик и проверка фактов не ждут, пока откроются все новые карточки
    assert taken == [4, 3, 1, 2]
