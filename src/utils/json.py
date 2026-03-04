# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json


def json_to_set(s: str | None) -> set:
    if not s:
        return set()

    if isinstance(s, list):
        return set(s)

    return set(json.loads(s))


def set_to_json(s: set | None) -> str | None:
    if not s:
        return None

    return json.dumps(sorted(list(s)))
