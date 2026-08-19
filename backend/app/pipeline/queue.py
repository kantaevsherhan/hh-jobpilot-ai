"""Персистентная очередь задач (§22).

Очередь живёт в таблице jobs, а не в памяти: прогон обязан переживать
паузу, остановку и падение приложения и продолжаться с места остановки.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import JobState, JobType, RunStatus
from app.storage.models import Job, Run
from app.storage.models.base import utcnow


async def add(
    session: AsyncSession,
    run_id: int,
    job_type: JobType | str,
    payload: dict[str, Any] | None = None,
) -> Job:
    job = Job(run_id=run_id, type=str(job_type), payload_json=payload or {})
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def add_many(
    session: AsyncSession,
    run_id: int,
    job_type: JobType | str,
    payloads: list[dict[str, Any]],
) -> int:
    for payload in payloads:
        session.add(Job(run_id=run_id, type=str(job_type), payload_json=payload))
    await session.commit()
    return len(payloads)


async def take_next(session: AsyncSession, run_id: int) -> Job | None:
    """Взять следующую задачу. Один воркер, последовательно: параллелизм
    упрётся в VRAM (§2)."""
    job = await session.scalar(
        select(Job)
        .where(Job.run_id == run_id, Job.state == JobState.PENDING.value)
        .order_by(Job.id)
        .limit(1)
    )
    if job is None:
        return None

    job.state = JobState.RUNNING.value
    job.started_at = utcnow()
    job.attempts += 1
    await session.commit()
    await session.refresh(job)
    return job


async def finish(
    session: AsyncSession,
    job: Job,
    state: JobState,
    error: str | None = None,
) -> None:
    job.state = state.value
    job.finished_at = utcnow()
    job.last_error = error
    await session.commit()


async def counts(session: AsyncSession, run_id: int) -> dict[str, int]:
    rows = await session.execute(
        select(Job.state, func.count()).where(Job.run_id == run_id).group_by(Job.state)
    )
    return {state: count for state, count in rows.all()}


async def pending_count(session: AsyncSession, run_id: int) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.run_id == run_id, Job.state == JobState.PENDING.value)
        )
    ) or 0


async def recover_after_crash(session: AsyncSession) -> dict[str, int]:
    """Восстановление после падения (§22).

    Задачи APPLY обратно в PENDING не возвращаются никогда: состояние
    отправленного отклика неизвестно, и повторять его вслепую нельзя.
    """
    runs = list(
        (await session.scalars(select(Run).where(Run.status == RunStatus.RUNNING.value))).all()
    )
    for run in runs:
        run.status = RunStatus.INTERRUPTED.value
        run.ended_at = utcnow()
        run.stop_reason = "INTERRUPTED"

    stuck = list(
        (await session.scalars(select(Job).where(Job.state == JobState.RUNNING.value))).all()
    )
    requeued = 0
    unknown = 0
    for job in stuck:
        if job.type == JobType.APPLY.value:
            job.state = JobState.FAILED.value
            job.last_error = "Приложение упало во время отклика, состояние неизвестно"
            unknown += 1
        else:
            job.state = JobState.PENDING.value
            requeued += 1

    if runs or stuck:
        await session.commit()

    return {"runs_interrupted": len(runs), "jobs_requeued": requeued, "applies_unknown": unknown}
