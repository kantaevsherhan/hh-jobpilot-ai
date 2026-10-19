"""Настраиваемое из UI: правила компаний, провайдеры, промпты, настройки."""

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import CompanyRuleAction, MatchType, ProviderType
from app.storage.models.base import Base, TimestampMixin
from app.storage.models.types import EncryptedString


class CompanyRule(Base, TimestampMixin):
    """Правило по названию компании (§12). resume_id NULL — правило для всех резюме."""

    __tablename__ = "company_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    match_type: Mapped[str] = mapped_column(String(20), default=MatchType.CONTAINS.value)
    value: Mapped[str] = mapped_column(String(300))
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    action: Mapped[str] = mapped_column(String(20), default=CompanyRuleAction.SKIP.value)
    score_delta: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class LLMProvider(Base, TimestampMixin):
    """Провайдер модели. Ключи хранятся тут, а не в .env — они правятся из UI (§29)."""

    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20), default=ProviderType.OLLAMA.value)
    base_url: Mapped[str | None] = mapped_column(String(300))
    # В базе лежит зашифрованным: копия базы не должна раскрывать ключи (§29)
    api_key: Mapped[str | None] = mapped_column(EncryptedString(500))
    model: Mapped[str | None] = mapped_column(String(150))
    temperature: Mapped[float] = mapped_column(default=0.3)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=300)
    extra_json: Mapped[dict[str, Any]] = mapped_column(default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Prompt(Base, TimestampMixin):
    """Промпт по ключу шага. Дефолты грузятся из app/prompts/*.md при первом старте."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)


class Setting(Base, TimestampMixin):
    """Настройки приложения одной таблицей ключ-значение.

    JSON вместо колонок: набор настроек меняется от фазы к фазе,
    и заводить миграцию ради каждого нового порога — лишнее.
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Skill(Base, TimestampMixin):
    """Скилл — набор правил стиля, который дописывается к выбранным промптам.

    Текст хранится как есть (вместе с frontmatter SKILL.md): пользователь вставляет
    файл целиком, а служебную шапку убирает подстановка.
    """

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    # Ключи промптов (PromptKey), к которым подключён скилл
    prompt_keys: Mapped[list[Any]] = mapped_column(default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
