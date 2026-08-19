"""Общие зависимости роутеров."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.session import get_session

Session = Annotated[AsyncSession, Depends(get_session)]
