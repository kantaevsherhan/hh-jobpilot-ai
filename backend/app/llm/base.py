"""Интерфейс провайдера модели и разбор её ответа."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.errors import AppError


@dataclass(slots=True)
class LLMResult:
    """Ответ модели: разобранный JSON и то, что она вернула на самом деле."""

    data: dict[str, Any]
    raw: str
    provider: str
    model: str | None = None
    elapsed_sec: float = 0.0
    retried: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Единый интерфейс всех пяти реализаций (§14).

    Провайдер не знает ни про браузер, ни про БД: получает текст промпта,
    возвращает текст ответа. Разбор и валидация — снаружи.
    """

    type: str = "base"

    def __init__(
        self,
        *,
        name: str,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.3,
        timeout_sec: int = 300,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.timeout_sec = timeout_sec
        self.extra = extra or {}

    @abstractmethod
    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        """Отправить промпт и вернуть сырой текст ответа."""

    async def close(self) -> None:
        """Освободить ресурсы. Большинству провайдеров освобождать нечего."""
        return None


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(raw: str) -> dict[str, Any]:
    """Достать JSON-объект из ответа модели.

    Маленькие модели любят обернуть JSON в ```-блок или дописать «Вот ответ:»,
    поэтому голого json.loads недостаточно.
    """
    text = raw.strip()

    block = _JSON_BLOCK.search(text)
    if block:
        text = block.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise AppError(
                "INVALID_LLM_RESPONSE",
                "Модель вернула ответ без JSON",
                technical_details=raw[:2000],
            ) from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AppError(
                "INVALID_LLM_RESPONSE",
                "JSON в ответе модели не разбирается",
                technical_details=f"{exc}\n{raw[:2000]}",
            ) from exc

    if not isinstance(parsed, dict):
        raise AppError(
            "INVALID_LLM_RESPONSE",
            "Модель вернула не объект",
            technical_details=raw[:2000],
        )
    return parsed
