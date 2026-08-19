"""Общие операции с таблицами.

Один набор функций на все ресурсы: дальше в проекте десяток однотипных
CRUD-экранов, и переписывать get/list/create/update руками для каждого —
это лишний код, в котором заводятся расхождения.
"""

from typing import Any, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.storage.models.base import Base

M = TypeVar("M", bound=Base)


async def get(session: AsyncSession, model: type[M], obj_id: Any) -> M | None:
    return await session.get(model, obj_id)


async def get_or_404(session: AsyncSession, model: type[M], obj_id: Any, what: str) -> M:
    obj = await session.get(model, obj_id)
    if obj is None:
        raise NotFoundError(what)
    return obj


async def list_all(
    session: AsyncSession,
    model: type[M],
    *,
    order_by: Any = None,
    **filters: Any,
) -> list[M]:
    stmt: Select[tuple[M]] = select(model)
    for field, value in filters.items():
        if value is not None:
            stmt = stmt.where(getattr(model, field) == value)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    return list((await session.scalars(stmt)).all())


async def count(session: AsyncSession, model: type[M], **filters: Any) -> int:
    stmt = select(func.count()).select_from(model)
    for field, value in filters.items():
        if value is not None:
            stmt = stmt.where(getattr(model, field) == value)
    return (await session.scalar(stmt)) or 0


async def create(session: AsyncSession, model: type[M], data: dict[str, Any]) -> M:
    obj = model(**data)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def update(session: AsyncSession, obj: M, data: dict[str, Any]) -> M:
    for field, value in data.items():
        setattr(obj, field, value)
    await session.commit()
    await session.refresh(obj)
    return obj


async def remove(session: AsyncSession, obj: M) -> None:
    await session.delete(obj)
    await session.commit()


async def remove_where(session: AsyncSession, model: type[M], **filters: Any) -> None:
    stmt = delete(model)
    for field, value in filters.items():
        stmt = stmt.where(getattr(model, field) == value)
    await session.execute(stmt)
