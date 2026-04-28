# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import re
import unicodedata
from dataclasses import fields
from typing import Any, Iterable, Tuple, get_origin, get_type_hints


# -------------------------------------------------------------
# Normalizers
# -------------------------------------------------------------
def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = unicodedata.normalize("NFKD", str(value))
    value = re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip().lower()

    return value or None


def normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    value = value.strip().lower()
    return value or None


def normalize_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "1"}:
            return True
        if v in {"false", "no", "0"}:
            return False
    raise TypeError(f"Invalid boolean value: {value}")


def normalize_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise TypeError(f"Invalid integer value: {value}")


def normalize_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            pass
    raise TypeError(f"Invalid float value: {value}")


def normalize_iterable(values: Iterable[str] | None) -> Tuple[str, ...]:
    if not values:
        return ()

    normalized = set()

    for v in values:
        if not isinstance(v, str):
            continue

        norm = normalize_text(v)
        if norm:
            normalized.add(norm)

    return tuple(sorted(normalized))


# -------------------------------------------------------------
# Validation
# -------------------------------------------------------------
def validate_entity_fields(
    entity: Any,
    data: dict[str, Any],
    required_fields: set[str] = frozenset(),
    to_remove: set[str] = frozenset(),
) -> dict[str, Any]:

    field_map = {f.name: f for f in fields(entity)}

    # Unknown fields
    unknown = set(data) - set(field_map)
    if unknown:
        raise ValueError(f"Unknown fields: {unknown}")

    # Missing required
    missing = required_fields - set(data)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    normalized_data: dict[str, Any] = {}

    type_hints = get_type_hints(entity)

    for name, field in field_map.items():

        if name in to_remove:
            continue

        if not field.init:
            continue

        value = data.get(name)

        if name in required_fields and value is None:
            raise ValueError(f"{name} is required and cannot be None.")

        field_type = type_hints.get(name, field.type)
        origin = get_origin(field_type)

        if field_type is str:
            normalized_data[name] = normalize_str(value)

        elif field_type is int:
            normalized_data[name] = normalize_int(value)

        elif field_type is float:
            normalized_data[name] = normalize_float(value)

        elif field_type is bool:
            normalized_data[name] = normalize_bool(value)

        elif origin in (tuple, list, set):
            if name == "keywords":
                normalized_data[name] = normalize_iterable(value)
            else:
                normalized_data[name] = value

        elif isinstance(value, (list, tuple, set)):
            if name == "keywords":
                normalized_data[name] = normalize_iterable(value)
            else:
                normalized_data[name] = value

        else:
            normalized_data[name] = value

    return normalized_data