"""Unit tests for app/services/ai/json_utils.py."""

from __future__ import annotations

import pytest

from app.services.ai.json_utils import AIInputError, AIParseError, extract_json


class TestExtractJson:
    def test_valid_json_returns_dict(self) -> None:
        result = extract_json('{"options": []}')
        assert result == {"options": []}

    def test_none_raises(self) -> None:
        with pytest.raises(AIParseError, match="empty/null"):
            extract_json(None)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(AIParseError, match="empty/null"):
            extract_json("")

    def test_markdown_fenced_json_with_lang(self) -> None:
        raw = '```json\n{"a": 1}\n```'
        assert extract_json(raw) == {"a": 1}

    def test_markdown_fenced_json_without_lang(self) -> None:
        raw = '```\n{"a": 1}\n```'
        assert extract_json(raw) == {"a": 1}

    def test_preamble_before_json(self) -> None:
        raw = 'Here is the result:\n{"a": 1}'
        assert extract_json(raw) == {"a": 1}

    def test_completely_invalid_raises(self) -> None:
        with pytest.raises(AIParseError):
            extract_json("Hello world, no JSON here")

    def test_nested_braces(self) -> None:
        raw = 'text {"a": {"b": 1}} text'
        assert extract_json(raw) == {"a": {"b": 1}}

    def test_parse_error_carries_raw_text(self) -> None:
        raw = "not json"
        with pytest.raises(AIParseError) as exc_info:
            extract_json(raw)
        assert exc_info.value.raw_text == raw

    def test_none_raw_text_on_empty_error(self) -> None:
        with pytest.raises(AIParseError) as exc_info:
            extract_json(None)
        assert exc_info.value.raw_text is None


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
