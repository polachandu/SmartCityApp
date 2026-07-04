"""
Unit tests for the utilities module.

Tests text truncation, JSON parsing from AI responses (including
markdown code fences), and secret masking.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add the .github directory to sys.path so we can import the ai package
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GITHUB_DIR = _REPO_ROOT / ".github"
if str(_GITHUB_DIR) not in sys.path:
    sys.path.insert(0, str(_GITHUB_DIR))

from ai.utils import mask_secret, safe_json_parse, truncate_text


# ---------------------------------------------------------------------------
# truncate_text Tests
# ---------------------------------------------------------------------------

class TestTruncateText:
    """Tests for the truncate_text function."""

    def test_short_text_unchanged(self) -> None:
        """Text shorter than max_length is returned unchanged."""
        assert truncate_text("Hello", 100) == "Hello"

    def test_exact_length_unchanged(self) -> None:
        """Text exactly at max_length is returned unchanged."""
        assert truncate_text("Hello", 5) == "Hello"

    def test_truncation_with_suffix(self) -> None:
        """Long text is truncated with default suffix."""
        result = truncate_text("Hello, World!", 8)
        assert result == "Hello..."
        assert len(result) == 8

    def test_custom_suffix(self) -> None:
        """Custom suffix is used when specified."""
        result = truncate_text("Hello, World!", 10, suffix=" [cut]")
        assert result == "Hell [cut]"

    def test_invalid_max_length_raises(self) -> None:
        """Raises ValueError when max_length <= suffix length."""
        with pytest.raises(ValueError, match="must be greater"):
            truncate_text("Hello", 2)

    def test_empty_text(self) -> None:
        """Empty text is returned unchanged."""
        assert truncate_text("", 100) == ""


# ---------------------------------------------------------------------------
# safe_json_parse Tests
# ---------------------------------------------------------------------------

class TestSafeJsonParse:
    """Tests for the safe_json_parse function."""

    def test_valid_json(self) -> None:
        """Parses valid JSON string directly."""
        result = safe_json_parse('{"score": 85, "decision": "APPROVE"}')
        assert result == {"score": 85, "decision": "APPROVE"}

    def test_json_in_code_fence(self) -> None:
        """Extracts JSON from markdown code fences."""
        text = '```json\n{"score": 85}\n```'
        result = safe_json_parse(text)
        assert result == {"score": 85}

    def test_json_in_plain_fence(self) -> None:
        """Extracts JSON from plain code fences (no language specifier)."""
        text = '```\n{"score": 85}\n```'
        result = safe_json_parse(text)
        assert result == {"score": 85}

    def test_json_with_surrounding_text(self) -> None:
        """Extracts JSON from text with surrounding content."""
        text = 'Here is my review:\n{"decision": "APPROVE", "score": 90}\nThat is all.'
        result = safe_json_parse(text)
        assert result is not None
        assert result["decision"] == "APPROVE"

    def test_invalid_json_returns_none(self) -> None:
        """Returns None for completely invalid JSON."""
        assert safe_json_parse("not json at all") is None

    def test_empty_string_returns_none(self) -> None:
        """Returns None for empty string."""
        assert safe_json_parse("") is None

    def test_none_like_returns_none(self) -> None:
        """Returns None for whitespace-only string."""
        assert safe_json_parse("   ") is None

    def test_json_array_returns_none(self) -> None:
        """Returns None for JSON arrays (we expect dicts)."""
        assert safe_json_parse("[1, 2, 3]") is None

    def test_nested_json(self) -> None:
        """Parses JSON with nested objects."""
        text = '{"outer": {"inner": "value"}, "list": [1, 2]}'
        result = safe_json_parse(text)
        assert result is not None
        assert result["outer"]["inner"] == "value"


# ---------------------------------------------------------------------------
# mask_secret Tests
# ---------------------------------------------------------------------------

class TestMaskSecret:
    """Tests for the mask_secret function."""

    def test_normal_secret(self) -> None:
        """Masks a normal-length secret, showing last 4 chars."""
        result = mask_secret("ghp_abc123xyz789")
        assert result.endswith("z789")
        assert "ghp_abc" not in result
        assert "*" in result

    def test_short_secret(self) -> None:
        """Short secrets are fully masked."""
        assert mask_secret("ab") == "****"
        assert mask_secret("abc") == "****"

    def test_exact_length(self) -> None:
        """Secret exactly at visible_chars length is fully masked."""
        assert mask_secret("abcd") == "****"

    def test_custom_visible_chars(self) -> None:
        """Custom visible_chars parameter works."""
        result = mask_secret("ghp_abc123xyz789", visible_chars=6)
        assert result.endswith("xyz789")

    def test_mask_length(self) -> None:
        """Masked result has correct total length."""
        secret = "ghp_1234567890"
        result = mask_secret(secret, visible_chars=4)
        assert len(result) == len(secret)
