# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json


def json_to_set(s: str | None) -> set[str] | None:
    if s is None:
        return None
    return set(json.loads(s))


def set_to_json(s: set[str] | None) -> str | None:
    if s is None:
        return None
    return json.dumps(sorted(list(s)))