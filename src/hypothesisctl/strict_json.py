import json
from pathlib import Path
from typing import Any

from .errors import ValidationError


MAX_BYTES = 1024 * 1024
MAX_DEPTH = 64


def _reject_float(value: str) -> None:
    raise ValidationError(f"floats are not supported: {value}")


def _reject_constant(value: str) -> None:
    raise ValidationError(f"non-finite numbers are not supported: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _check_depth(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, parent_depth = stack.pop()
        if isinstance(current, dict):
            depth = parent_depth + 1
            if depth > MAX_DEPTH:
                raise ValidationError(f"JSON nesting exceeds {MAX_DEPTH} levels")
            stack.extend((child, depth) for child in current.values())
        elif isinstance(current, list):
            depth = parent_depth + 1
            if depth > MAX_DEPTH:
                raise ValidationError(f"JSON nesting exceeds {MAX_DEPTH} levels")
            stack.extend((child, depth) for child in current)


def loads_strict(data: bytes) -> Any:
    if len(data) > MAX_BYTES:
        raise ValidationError(f"input exceeds {MAX_BYTES} bytes")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValidationError("input is not valid UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ValidationError:
        raise
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValidationError(f"invalid JSON: {error}") from error
    _check_depth(value)
    return value


def load_file(path: str | Path) -> Any:
    candidate = Path(path)
    try:
        if not candidate.is_file():
            raise ValidationError(f"record is not a regular file: {candidate}")
        size = candidate.stat().st_size
        if size > MAX_BYTES:
            raise ValidationError(f"input exceeds {MAX_BYTES} bytes")
        return loads_strict(candidate.read_bytes())
    except ValidationError:
        raise
    except OSError as error:
        raise ValidationError(f"could not read record {candidate}: {error}") from error
