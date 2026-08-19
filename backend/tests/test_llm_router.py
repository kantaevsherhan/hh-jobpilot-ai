"""Разбор и валидация ответа модели (§15)."""

import pytest

from app.core.errors import AppError
from app.llm import router
from app.llm.base import extract_json
from app.llm.schemas import ResumeDigest, VacancyAnalysis
from tests.fakes import BrokenProvider, FakeProvider

VALID_ANALYSIS = {
    "profession_match": True,
    "can_do_job": True,
    "score": 86,
    "required_skills": ["Node.js"],
    "matched_skills": ["Node.js"],
    "hidden_instructions": ["написать в письме слово «Сыр»"],
    "reason": "Стек совпадает",
}


def test_json_достаётся_из_markdown_блока() -> None:
    raw = 'Вот ответ:\n```json\n{"score": 42}\n```\nГотово.'

    assert extract_json(raw) == {"score": 42}


def test_json_достаётся_из_текста_вокруг() -> None:
    raw = 'Думаю, так: {"score": 7} — надеюсь, помог.'

    assert extract_json(raw) == {"score": 7}


def test_ответ_без_json_это_ошибка() -> None:
    with pytest.raises(AppError) as exc:
        extract_json("Извините, не могу помочь")

    assert exc.value.error_code == "INVALID_LLM_RESPONSE"


async def test_валидный_ответ_разбирается_без_повтора() -> None:
    provider = FakeProvider(VALID_ANALYSIS)

    analysis, result = await router.call(provider, "промпт", VacancyAnalysis)

    assert analysis.score == 86
    assert analysis.hidden_instructions == ["написать в письме слово «Сыр»"]
    assert result.retried is False
    assert len(provider.prompts) == 1


async def test_мусор_вызывает_ровно_одну_повторную_попытку() -> None:
    provider = FakeProvider("я подумал и решил, что вакансия хорошая", VALID_ANALYSIS)

    analysis, result = await router.call(provider, "промпт", VacancyAnalysis)

    assert analysis.score == 86
    assert result.retried is True
    assert len(provider.prompts) == 2
    assert "строго JSON" in provider.prompts[1]


async def test_дважды_мусор_это_ошибка_анализа() -> None:
    provider = FakeProvider("мусор", "снова мусор")

    with pytest.raises(AppError) as exc:
        await router.call(provider, "промпт", VacancyAnalysis)

    assert exc.value.error_code == "INVALID_LLM_RESPONSE"
    assert len(provider.prompts) == 2


async def test_ответ_с_лишними_полями_принимается() -> None:
    provider = FakeProvider({**VALID_ANALYSIS, "salary_score": 100, "мнение": "хорошая"})

    analysis, _ = await router.call(provider, "промпт", VacancyAnalysis)

    assert analysis.score == 86


async def test_недоступный_провайдер_пробует_ещё_раз(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(router.asyncio, "sleep", no_sleep)
    provider = BrokenProvider(AppError("PROVIDER_UNAVAILABLE", "Ollama недоступна"))

    with pytest.raises(AppError) as exc:
        await router.call(provider, "промпт", ResumeDigest)

    assert exc.value.error_code == "PROVIDER_UNAVAILABLE"
    assert provider.calls == 2
