"""События прогона: лента для UI и разбор полётов (§22, §27)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EventLevel
from app.storage.models import RunEvent


async def log_event(
    session: AsyncSession,
    run_id: int,
    event_type: str,
    message: str,
    *,
    level: EventLevel | str = EventLevel.INFO,
    resume_vacancy_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> RunEvent:
    event = RunEvent(
        run_id=run_id,
        resume_vacancy_id=resume_vacancy_id,
        level=str(level),
        type=event_type,
        message=message,
        payload_json=payload,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def read_after(
    session: AsyncSession,
    run_id: int,
    after_id: int = 0,
    limit: int = 200,
) -> list[RunEvent]:
    """Инкрементальное чтение ленты: всё сразу в один ответ не грузим (§2)."""
    rows = await session.scalars(
        select(RunEvent)
        .where(RunEvent.run_id == run_id, RunEvent.id > after_id)
        .order_by(RunEvent.id)
        .limit(limit)
    )
    return list(rows.all())
