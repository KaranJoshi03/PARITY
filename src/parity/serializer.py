"""Type-tagged JSON serialization per CONTRACTS.md.

Every value is stored as {"t": <type tag>, "v": <value>}.
Tags: none, bool, int, long, float, str (py2 byte string), unicode,
      bytes3 (py3 bytes), str3 (py3 text), list, tuple,
      dict (ordered pairs list), set (sorted list with ordering note),
      exception, repr_fallback.
"""

import json
from typing import Any


# Exhaustive set of valid type tags from CONTRACTS.md
VALID_TYPE_TAGS = frozenset({
    "none",
    "bool",
    "int",
    "long",
    "float",
    "str",           # py2 byte string
    "unicode",       # py2 unicode string
    "bytes3",        # py3 bytes
    "str3",          # py3 text
    "list",
    "tuple",
    "dict",          # stored as ordered pairs list
    "set",           # stored as sorted list with ordering note
    "exception",
    "repr_fallback",
})


class SerializationError(Exception):
    """Raised on invalid type-tagged values."""
    pass


def validate_type_tag(tag: str) -> None:
    """Raise SerializationError if tag is not in the CONTRACTS.md tag set."""
    if not isinstance(tag, str):
        raise SerializationError(
            f"Type tag must be a string, got {type(tag).__name__}"
        )
    if tag not in VALID_TYPE_TAGS:
        raise SerializationError(
            f"Invalid type tag '{tag}'. Valid tags: {sorted(VALID_TYPE_TAGS)}"
        )


def validate_tagged_value(d: Any, *, name: str = "value") -> None:
    """Validate that d is a well-formed type-tagged value {"t": ..., "v": ...}.

    Validates both tag validity and payload conformance per CONTRACTS.md.
    Raises SerializationError on any violation.
    """
    if not isinstance(d, dict):
        raise SerializationError(
            f"{name}: type-tagged value must be a dict, got {type(d).__name__}"
        )
    keys = set(d.keys())
    if keys != {"t", "v"}:
        extra = keys - {"t", "v"}
        missing = {"t", "v"} - keys
        parts = []
        if missing:
            parts.append(f"missing keys: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected keys: {sorted(extra)}")
        raise SerializationError(f"{name}: {'; '.join(parts)}")
    tag = d["t"]
    validate_type_tag(tag)

    val = d["v"]
    if tag == "none":
        if val is not None:
            raise SerializationError(
                f"{name}: tag 'none' requires value None, got {type(val).__name__}"
            )
    elif tag == "bool":
        if not isinstance(val, bool):
            raise SerializationError(
                f"{name}: tag 'bool' requires bool value, got {type(val).__name__}"
            )
    elif tag in ("int", "long"):
        if isinstance(val, bool) or not isinstance(val, int):
            raise SerializationError(
                f"{name}: tag '{tag}' requires int value, got {type(val).__name__}"
            )
    elif tag == "float":
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise SerializationError(
                f"{name}: tag 'float' requires numeric value, got {type(val).__name__}"
            )
    elif tag in ("str", "unicode", "str3", "repr_fallback"):
        if not isinstance(val, str):
            raise SerializationError(
                f"{name}: tag '{tag}' requires str value, got {type(val).__name__}"
            )
    elif tag == "bytes3":
        if not isinstance(val, (str, list, bytes)):
            raise SerializationError(
                f"{name}: tag 'bytes3' requires str, list, or bytes, got {type(val).__name__}"
            )

    elif tag in ("list", "tuple"):
        if not isinstance(val, (list, tuple)):
            raise SerializationError(
                f"{name}: tag '{tag}' requires list/tuple, got {type(val).__name__}"
            )
    elif tag == "dict":
        if not isinstance(val, list):
            raise SerializationError(
                f"{name}: tag 'dict' requires ordered pairs list, got {type(val).__name__}"
            )
    elif tag == "set":
        if not isinstance(val, (list, dict)):
            raise SerializationError(
                f"{name}: tag 'set' requires list or dict payload, got {type(val).__name__}"
            )
    elif tag == "exception":
        if not isinstance(val, dict):
            raise SerializationError(
                f"{name}: tag 'exception' requires dict payload, got {type(val).__name__}"
            )


def make_tagged(tag: str, value: Any) -> dict:
    """Create a type-tagged value dict. Validates the tag and value payload."""
    tagged = {"t": tag, "v": value}
    validate_tagged_value(tagged)
    return tagged


def is_tagged_value(d: Any) -> bool:
    """Return True if d is a valid, payload-conforming type-tagged value."""
    try:
        validate_tagged_value(d)
        return True
    except SerializationError:
        return False



def tagged_to_json(tagged: dict, **kwargs) -> str:
    """Serialize a type-tagged value to a JSON string."""
    validate_tagged_value(tagged)
    return json.dumps(tagged, ensure_ascii=False, **kwargs)


def tagged_from_json(s: str) -> dict:
    """Deserialize a JSON string to a validated type-tagged value."""
    d = json.loads(s)
    validate_tagged_value(d)
    return d
