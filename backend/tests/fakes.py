"""Подделки внешних зависимостей: модель и провайдер.

Тесты не поднимают Ollama и не ходят в сеть — сюда кладётся заранее
заготовленный ответ, и он возвращается вместо реального вызова.
"""

import json
from typing import Any

from app.llm.base import LLMProvider


class FakeProvider(LLMProvider):
    """Отдаёт заготовленные ответы по очереди и считает вызовы."""

    type = "fake"

    def __init__(self, *responses: str | dict[str, Any], name: str = "fake") -> None:
        super().__init__(name=name, model="fake-model")
        self.responses = [r if isinstance(r, str) else json.dumps(r) for r in responses]
        self.prompts: list[str] = []

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        self.prompts.append(prompt)
        index = min(len(self.prompts) - 1, len(self.responses) - 1)
        return self.responses[index]


class BrokenProvider(LLMProvider):
    """Всегда падает заданной ошибкой — для проверки поведения при сбое."""

    type = "broken"

    def __init__(self, error: Exception, name: str = "broken") -> None:
        super().__init__(name=name)
        self.error = error
        self.calls = 0

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        self.calls += 1
        raise self.error
