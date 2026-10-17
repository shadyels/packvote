"""Unit tests for app/services/ai/json_utils.py."""

from __future__ import annotations

import pytest

from app.services.ai.json_utils import AIInputError, AIParseError, extract_json


class TestExtractJson:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ('{"options": []}', {"options": []}),
            ('```json\n{"a": 1}\n```', {"a": 1}),  # fenced, with lang
            ('```\n{"a": 1}\n```', {"a": 1}),  # fenced, no lang
            ('Here is the result:\n{"a": 1}', {"a": 1}),  # preamble
            ('text {"a": {"b": 1}} text', {"a": {"b": 1}}),  # nested braces
        ],
        ids=["plain", "fenced_lang", "fenced", "preamble", "nested"],
    )
    def test_extracts_json(self, raw: str, expected: dict) -> None:
        assert extract_json(raw) == expected

    @pytest.mark.parametrize("raw", [None, ""])
    def test_empty_raises(self, raw: str | None) -> None:
        with pytest.raises(AIParseError, match="empty/null"):
            extract_json(raw)

    def test_completely_invalid_raises(self) -> None:
        with pytest.raises(AIParseError):
            extract_json("Hello world, no JSON here")


class TestAIInputError:
    def test_is_subclass_of_ai_parse_error(self) -> None:
        err = AIInputError("Bad destination", "Try Paris, France", "destination")
        assert isinstance(err, AIParseError)

    def test_attributes_stored_correctly(self) -> None:
        err = AIInputError(
            message="Unknown destination",
            suggestion="Try 'Kyoto, Japan'",
            field="destination",
        )
        assert err.ai_message == "Unknown destination"
        assert err.suggestion == "Try 'Kyoto, Japan'"
        assert err.field == "destination"

    def test_defaults(self) -> None:
        err = AIInputError("Something went wrong")
        assert err.suggestion == ""
        assert err.field == "general"

    def test_str_message(self) -> None:
        err = AIInputError("Bad input")
        assert str(err) == "Bad input"
