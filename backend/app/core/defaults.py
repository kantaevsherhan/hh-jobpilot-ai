"""Значения настроек по умолчанию.

Всё это правится из UI и лежит в таблице settings. Здесь только то,
с чем приложение стартует на пустой базе (§33 п.6: не хардкодить пороги
в коде — код читает их отсюда один раз, дальше из БД).
"""

from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    # Задержки между действиями браузера (§20). Все — диапазоны
    "delays": {
        "speed_multiplier": 1.0,
        "long_pause_every": 12,
        "long_pause_range": [45, 120],
        "ranges": {
            "page_load": [1.0, 2.5],
            "between_vacancies": [3, 8],
            "between_search_pages": [2, 5],
            "before_open_form": [2, 4],
            "before_submit": [2, 5],
            "after_apply": [10, 20],
            "typing_per_char": [0.01, 0.04],
            "on_error": [3, 10],
        },
    },
    "limits": {
        "max_applications_per_run": 20,
        "max_applications_per_day": 30,
        "max_consecutive_errors": 5,
    },
    # Курсы правятся руками раз в месяц: внешних API за курсом в v1 нет (§11)
    "currency_rates": {"KZT": 1.0, "RUB": 5.7, "USD": 500.0, "EUR": 540.0},
    "tax_rate": 0.10,
    "llm": {
        "max_vacancy_chars": 6000,
        "letter_min_chars": 400,
        "letter_max_chars": 800,
        # strict | moderate | bold — см. app/llm/embellishment.py
        "letter_embellishment": "moderate",
    },
    # step -> llm_providers.id. Пусто, пока провайдеры не заведены
    "llm_routing": {},
    "bot": {
        "answer_employer_questions": False,
        # broad — откликаться и на частичное совпадение, strict — только на уверенное
        "apply_breadth": "broad",
    },
}


# Провайдер, который создаётся на пустой базе. Дальше правится из UI:
# адрес, модель и num_ctx хранятся в строке llm_providers, а не в .env
DEFAULT_PROVIDER: dict[str, Any] = {
    "name": "Локальная Ollama",
    "type": "ollama",
    "base_url": "http://localhost:11434",
    "model": "qwen3:4b-instruct",
    "temperature": 0.3,
    "timeout_sec": 300,
    "extra_json": {"num_ctx": 8192, "keep_alive": "30m"},
    "is_enabled": True,
}
