"""Задержки между действиями браузера (§20).

Это ограничение нагрузки на чужой сервер, а не маскировка. Каждая пауза —
диапазон, фактическое значение выбирается случайно внутри него: ровные
интервалы бьют по серверу одинаковыми пачками.
"""

import asyncio
import random
from dataclasses import dataclass
from typing import Any

from app.core.defaults import DEFAULT_SETTINGS

# Полностью обнулить задержки нельзя
MIN_MULTIPLIER = 0.1
MAX_MULTIPLIER = 3.0


@dataclass(frozen=True, slots=True)
class DelayRange:
    min_sec: float
    max_sec: float

    def pick(self, multiplier: float = 1.0) -> float:
        factor = clamp_multiplier(multiplier)
        low, high = sorted((self.min_sec, self.max_sec))
        return random.uniform(low, high) * factor


def clamp_multiplier(value: float) -> float:
    return max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, value))


class Delays:
    """Настройки задержек, применяются со следующей задачи без перезапуска."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        defaults: dict[str, Any] = DEFAULT_SETTINGS["delays"]
        merged = {**defaults, **(config or {})}
        merged["ranges"] = {**defaults["ranges"], **(config or {}).get("ranges", {})}

        self.multiplier = clamp_multiplier(float(merged.get("speed_multiplier", 1.0)))
        self.long_pause_every = int(merged.get("long_pause_every", 12))
        low, high = merged.get("long_pause_range", [45, 120])
        self.long_pause = DelayRange(float(low), float(high))
        self.ranges = {
            key: DelayRange(float(value[0]), float(value[1]))
            for key, value in merged["ranges"].items()
        }

    def seconds(self, key: str) -> float:
        """Сколько ждать по этому ключу. Неизвестный ключ — не повод падать."""
        delay = self.ranges.get(key)
        return delay.pick(self.multiplier) if delay else 0.0

    async def pause(self, key: str) -> float:
        seconds = self.seconds(key)
        await asyncio.sleep(seconds)
        return seconds

    async def long_break(self) -> float:
        seconds = self.long_pause.pick(self.multiplier)
        await asyncio.sleep(seconds)
        return seconds

    def needs_long_break(self, processed: int) -> bool:
        return (
            processed > 0 and self.long_pause_every > 0 and processed % self.long_pause_every == 0
        )

    def estimate_run_minutes(self, vacancies: int, llm_seconds_per_vacancy: float = 120) -> int:
        """Оценка длительности прогона для подсказки в UI (§29)."""
        per_vacancy = (
            self.ranges["between_vacancies"].pick(self.multiplier)
            + self.ranges["page_load"].pick(self.multiplier)
            + llm_seconds_per_vacancy
        )
        breaks = (vacancies // self.long_pause_every) if self.long_pause_every else 0
        total = vacancies * per_vacancy + breaks * self.long_pause.pick(self.multiplier)
        return max(1, round(total / 60))
