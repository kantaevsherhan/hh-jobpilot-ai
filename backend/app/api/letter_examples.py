"""Примеры писем пользователя — ориентир стиля для модели (§17)."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import Session
from app.storage.models import LetterExample
from app.storage.repositories import crud

router = APIRouter(prefix="/letter-examples", tags=["Примеры писем"])

CATEGORIES = ["Backend", "Fullstack", "Go", "Стартап", "Энтерпрайз", "Общий"]


class ExampleIn(BaseModel):
    resume_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    category: str = "Общий"
    tone: str = "Нейтральный"
    content: str = Field(min_length=1)
    is_active: bool = True
    is_preferred: bool = False


class ExamplePatch(BaseModel):
    name: str | None = None
    category: str | None = None
    tone: str | None = None
    content: str | None = None
    is_active: bool | None = None
    is_preferred: bool | None = None


class ExampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int | None
    name: str
    category: str
    tone: str
    content: str
    is_active: bool
    is_preferred: bool


@router.get("", response_model=list[ExampleOut], summary="Список примеров")
async def list_examples(session: Session, resume_id: int | None = None) -> list[LetterExample]:
    rows = await crud.list_all(session, LetterExample, order_by=LetterExample.id)
    if resume_id is None:
        return rows
    return [row for row in rows if row.resume_id in (None, resume_id)]


@router.get("/categories", summary="Доступные категории")
async def categories() -> list[str]:
    return CATEGORIES


@router.post("", response_model=ExampleOut, status_code=201, summary="Добавить пример")
async def create_example(payload: ExampleIn, session: Session) -> LetterExample:
    return await crud.create(session, LetterExample, payload.model_dump())


@router.patch("/{example_id}", response_model=ExampleOut, summary="Изменить пример")
async def patch_example(example_id: int, payload: ExamplePatch, session: Session) -> LetterExample:
    row = await crud.get_or_404(session, LetterExample, example_id, "Пример письма")
    return await crud.update(session, row, payload.model_dump(exclude_unset=True))


@router.delete("/{example_id}", status_code=204, summary="Удалить пример")
async def delete_example(example_id: int, session: Session) -> None:
    row = await crud.get_or_404(session, LetterExample, example_id, "Пример письма")
    await crud.remove(session, row)
