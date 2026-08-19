"""Фабрики тестовых объектов с разумными дефолтами.

Тест указывает только то, что проверяет, остальное берётся отсюда.
"""

from typing import Any

from app.storage.models import Resume, Vacancy


def make_resume(**overrides: Any) -> Resume:
    data: dict[str, Any] = {
        "name": "Backend Node.js",
        "raw_text": "Fullstack разработчик, 4 года. TypeScript, Vue, Node.js, Go, PostgreSQL.",
        "allowed_facts": "Готов к переезду в Алматы",
        "letter_languages": ["ru"],
        "min_score": 75,
        "auto_apply_score": 90,
    }
    data.update(overrides)
    return Resume(**data)


def make_vacancy(**overrides: Any) -> Vacancy:
    data: dict[str, Any] = {
        "hh_id": "100500",
        "url": "https://hh.kz/vacancy/100500",
        "title": "Backend Developer",
        "company_name": "ТОО ABC",
        "description": "Требуется backend-разработчик на Node.js." * 10,
        "salary_from": 700_000,
        "salary_to": 900_000,
        "currency": "KZT",
        "salary_gross": False,
    }
    data.update(overrides)
    return Vacancy(**data)
