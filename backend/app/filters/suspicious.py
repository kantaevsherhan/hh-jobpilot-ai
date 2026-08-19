"""Жёсткие правила скам-детекта — кодом, без модели (§13).

Подозрительная вакансия не выбрасывается: она сохраняется со статусом
«Подозрительная» и попадает в отдельный список, чтобы её можно было
просмотреть глазами.
"""

import re

MIN_DESCRIPTION_CHARS = 300

PRIVATE_PERSON_MARKERS = ("частное лицо", "частный", "физическое лицо", "жеке тұлға")

MESSENGER_ONLY = re.compile(
    r"(пишите|звоните|напишите|обращайтесь)[^.!?\n]{0,60}"
    r"(whatsapp|ватсап|telegram|телеграм|вотсап|viber|вайбер)",
    re.IGNORECASE,
)

REQUIREMENT_MARKERS = (
    "требовани",
    "обязанност",
    "что нужно",
    "ожидаем",
    "от вас",
    "задачи",
    "стек",
    "опыт работы",
)


def check_suspicious(
    *,
    title: str,
    description: str,
    company_name: str | None,
    apply_is_external: bool = False,
) -> list[str]:
    """Вернуть список сработавших признаков. Пустой список — вакансия чистая."""
    reasons: list[str] = []
    text = f"{title}\n{description}"
    lowered = text.lower()

    if len(description.strip()) < MIN_DESCRIPTION_CHARS:
        reasons.append(f"Описание короче {MIN_DESCRIPTION_CHARS} символов")

    if not company_name or not company_name.strip():
        reasons.append("Компания не указана")
    elif any(marker in company_name.lower() for marker in PRIVATE_PERSON_MARKERS):
        reasons.append("Работодатель — частное лицо")

    has_requirements = any(marker in lowered for marker in REQUIREMENT_MARKERS)
    if MESSENGER_ONLY.search(text) and not has_requirements:
        reasons.append("Нет требований, только просьба написать в мессенджер")

    if apply_is_external:
        reasons.append("Кнопка отклика ведёт на внешний сайт")

    return reasons
