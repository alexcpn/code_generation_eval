"""
CHALLENGE: Text Normalizer with Unicode and Edge Cases
CATEGORY: edge_cases
DIFFICULTY: 2
POINTS: 10
WHY: Models treat strings as ASCII. Real-world text has Unicode whitespace, zero-width
     characters, mixed encodings, emoji, and combining characters. Models that generate
     text-processing code almost always fail on these inputs.
"""

PROMPT = """
Write a function `normalize_text(text: str) -> str` that normalizes user-input text:

1. Strip leading/trailing whitespace (including Unicode whitespace like \\u00A0, \\u2003)
2. Collapse all internal whitespace sequences (including Unicode whitespace) into a single space
3. Remove zero-width characters (\\u200B, \\u200C, \\u200D, \\uFEFF)
4. Normalize Unicode to NFC form
5. Return the result

Also write `safe_truncate(text: str, max_bytes: int) -> str` that:
1. Truncates a string so its UTF-8 encoding is at most max_bytes
2. Never cuts in the middle of a multi-byte character
3. Never cuts in the middle of a grapheme cluster (e.g., emoji with skin tone modifiers)
4. Returns the longest valid prefix that fits

Requirements:
- Handle None input by returning ""
- Handle empty string by returning ""
- Preserve case — do not lowercase
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib
import unicodedata


def load():
    mod = importlib.import_module("solutions.c03_edge_cases")
    return mod.normalize_text, mod.safe_truncate


class TestNormalizeText:
    """6 points."""

    def test_basic_whitespace(self):
        """(1 pt) Simple extra spaces."""
        normalize, _ = load()
        assert normalize("  hello   world  ") == "hello world"

    def test_unicode_whitespace(self):
        """(1 pt) Non-breaking space, em space, etc."""
        normalize, _ = load()
        text = "\u00A0\u2003hello\u00A0\u00A0world\u2003"
        assert normalize(text) == "hello world"

    def test_zero_width_characters(self):
        """(1 pt) Remove zero-width chars but keep visible text."""
        normalize, _ = load()
        text = "hel\u200Blo\u200Cwo\u200Drld\uFEFF"
        assert normalize(text) == "helloworld"

    def test_nfc_normalization(self):
        """(1 pt) é as e+combining-accent should become single é."""
        normalize, _ = load()
        # e followed by combining acute accent
        text = "caf\u0065\u0301"
        result = normalize(text)
        assert result == "caf\u00E9"  # NFC form
        assert len(result) == 4

    def test_none_input(self):
        """(1 pt) None returns empty string."""
        normalize, _ = load()
        assert normalize(None) == ""

    def test_empty_and_whitespace_only(self):
        """(1 pt) Empty and whitespace-only return empty."""
        normalize, _ = load()
        assert normalize("") == ""
        assert normalize("   \u00A0\u2003  ") == ""


class TestSafeTruncate:
    """4 points."""

    def test_ascii_truncation(self):
        """(1 pt) Simple ASCII truncation."""
        _, truncate = load()
        assert truncate("hello world", 5) == "hello"

    def test_multibyte_no_split(self):
        """(1 pt) Don't cut in the middle of a multi-byte UTF-8 character."""
        _, truncate = load()
        # "café" — é is 2 bytes in UTF-8, total = 5 bytes (c=1,a=1,f=1,é=2)
        result = truncate("café", 4)
        # Can fit "caf" (3 bytes) but not "café" (5 bytes)
        assert result == "caf"
        assert len(result.encode("utf-8")) <= 4

    def test_emoji_no_split(self):
        """(1 pt) Don't cut in the middle of an emoji."""
        _, truncate = load()
        # 👨‍👩‍👧 is a family emoji (ZWJ sequence): 👨 + ZWJ + 👩 + ZWJ + 👧
        # Each person is 4 bytes, each ZWJ is 3 bytes = 18 bytes total
        family = "👨\u200D👩\u200D👧"
        result = truncate("A" + family, 5)
        # Can only fit "A" (1 byte), not the full family emoji
        assert result == "A"

    def test_skin_tone_modifier(self):
        """(1 pt) Don't split emoji from its skin tone modifier."""
        _, truncate = load()
        # 👋🏽 = wave (4 bytes) + skin tone (4 bytes) = 8 bytes, one grapheme
        wave = "👋🏽"
        result = truncate(wave, 6)
        # 6 bytes is not enough for the full grapheme (8 bytes), so return ""
        assert result == ""
        assert len(result.encode("utf-8")) <= 6
