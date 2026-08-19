"""Справочники кодов для интерфейса: код → русская подпись.

Фронтенд не хранит копию списка статусов, а забирает его отсюда —
иначе подписи разъезжаются при каждом изменении §24.
"""

from typing import Any

from fastapi import APIRouter

from app.core import enums

router = APIRouter(tags=["Справочники"])


@router.get("/dictionaries", summary="Все справочники кодов с русскими подписями")
async def get_dictionaries() -> dict[str, Any]:
    return {
        "vacancy_status": enums.VACANCY_STATUS_LABELS,
        "skip_reason": enums.SKIP_REASON_LABELS,
        "hh_application_status": enums.HH_APPLICATION_STATUS_LABELS,
        "error_code": enums.ERROR_CODE_LABELS,
        "run_status": enums.RUN_STATUS_LABELS,
        "stop_reason": enums.STOP_REASON_LABELS,
        "bot_mode": enums.BOT_MODE_LABELS,
        "runtime_mode": enums.RUNTIME_MODE_LABELS,
        "remote_mode": enums.REMOTE_MODE_LABELS,
        "work_format": enums.WORK_FORMAT_LABELS,
        "company_rule_action": enums.COMPANY_RULE_ACTION_LABELS,
        "letter_source": enums.LETTER_SOURCE_LABELS,
        "prompt_key": enums.PROMPT_KEY_LABELS,
    }
