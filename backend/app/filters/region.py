"""Казахстан по справочнику HH; язык и валюта не доказывают страну."""

import json
from pathlib import Path
from typing import Any

_AREAS = json.loads(Path(__file__).with_name("kazakhstan_areas.json").read_text(encoding="utf-8"))
_KZ_IDS = frozenset(_AREAS["area_ids"])
_KZ_NAMES = frozenset(_AREAS["unambiguous_names"])


def is_kazakhstan(area: str | None, raw_json: dict[str, Any] | None) -> bool:
    raw_area = (raw_json or {}).get("area")
    if isinstance(raw_area, dict) and raw_area.get("id") is not None:
        # Явный ID важнее текста адреса; неизвестный ID не подтверждает страну.
        return str(raw_area["id"]) in _KZ_IDS
    # DOM возвращает адрес целиком. Неоднозначные населённые пункты исключены
    # при подготовке справочника, так как они встречаются и в других странах.
    locality = (area or "").split(",", 1)[0].strip().casefold()
    return locality in _KZ_NAMES
