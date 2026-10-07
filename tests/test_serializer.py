"""Tests for type-tagged JSON serialization (CONTRACTS.md § Serialization)."""

import pytest

from parity.serializer import (
    VALID_TYPE_TAGS,
    SerializationError,
    is_tagged_value,
    make_tagged,
    tagged_from_json,
    tagged_to_json,
    validate_tagged_value,
    validate_type_tag,
)


# ---------------------------------------------------------------------------
# validate_type_tag
# ---------------------------------------------------------------------------

class TestValidateTypeTag:

    @pytest.mark.parametrize("tag", sorted(VALID_TYPE_TAGS))
    def test_all_valid_tags_accepted(self, tag):
        validate_type_tag(tag)  # should not raise

    def test_invalid_tag_rejected(self):
        with pytest.raises(SerializationError, match="Invalid type tag"):
            validate_type_tag("invalid_tag")

    def test_empty_string_rejected(self):
        with pytest.raises(SerializationError, match="Invalid type tag"):
            validate_type_tag("")

    def test_non_string_rejected(self):
        with pytest.raises(SerializationError, match="must be a string"):
            validate_type_tag(42)


# ---------------------------------------------------------------------------
# validate_tagged_value
# ---------------------------------------------------------------------------

class TestValidateTaggedValue:

    def test_valid_int(self):
        validate_tagged_value({"t": "int", "v": 42})

    def test_valid_none(self):
        validate_tagged_value({"t": "none", "v": None})

    def test_valid_repr_fallback(self):
        validate_tagged_value({"t": "repr_fallback", "v": "<object at 0x...>"})

    def test_not_dict_rejected(self):
        with pytest.raises(SerializationError, match="must be a dict"):
            validate_tagged_value([1, 2])

    def test_missing_t_rejected(self):
        with pytest.raises(SerializationError, match="missing keys"):
            validate_tagged_value({"v": 42})

    def test_missing_v_rejected(self):
        with pytest.raises(SerializationError, match="missing keys"):
            validate_tagged_value({"t": "int"})

    def test_extra_key_rejected(self):
        with pytest.raises(SerializationError, match="unexpected keys"):
            validate_tagged_value({"t": "int", "v": 42, "extra": True})

    def test_invalid_tag_in_value_rejected(self):
        with pytest.raises(SerializationError, match="Invalid type tag"):
            validate_tagged_value({"t": "INVALID", "v": 42})


# ---------------------------------------------------------------------------
# make_tagged
# ---------------------------------------------------------------------------

class TestMakeTagged:

    def test_creates_correct_dict(self):
        result = make_tagged("str3", "hello")
        assert result == {"t": "str3", "v": "hello"}

    def test_invalid_tag_raises(self):
        with pytest.raises(SerializationError):
            make_tagged("bad_tag", "value")


# ---------------------------------------------------------------------------
# is_tagged_value
# ---------------------------------------------------------------------------

class TestIsTaggedValue:

    def test_valid_returns_true(self):
        assert is_tagged_value({"t": "int", "v": 42}) is True

    def test_missing_key_returns_false(self):
        assert is_tagged_value({"t": "int"}) is False

    def test_extra_key_returns_false(self):
        assert is_tagged_value({"t": "int", "v": 42, "x": 1}) is False

    def test_bad_tag_returns_false(self):
        assert is_tagged_value({"t": "NOPE", "v": 1}) is False

    def test_non_dict_returns_false(self):
        assert is_tagged_value("not a dict") is False


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

class TestJsonRoundTrip:

    @pytest.mark.parametrize("tag,value", [
        ("none", None),
        ("bool", True),
        ("int", -7),
        ("long", 2**63),
        ("float", 3.14),
        ("str", "byte string"),
        ("unicode", "héllo"),
        ("bytes3", [104, 101, 108]),
        ("str3", "text"),
        ("list", [1, 2, 3]),
        ("tuple", [1, "a"]),
        ("dict", [["key", "val"]]),
        ("set", [1, 2, 3]),
        ("exception", {"class": "ValueError", "message": "bad"}),
        ("repr_fallback", "<object>"),
    ])
    def test_round_trip(self, tag, value):
        tagged = make_tagged(tag, value)
        json_str = tagged_to_json(tagged)
        restored = tagged_from_json(json_str)
        assert restored == tagged

    def test_from_json_rejects_malformed(self):
        with pytest.raises(SerializationError):
            tagged_from_json('{"t": "FAKE", "v": 1}')
