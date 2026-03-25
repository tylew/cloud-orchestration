"""Unit tests for secret masking logic."""

from packages.platform.gcp.secret_manager import mask_secret_value, safe_mask


class TestSafeMask:
    def test_short_secret_returns_none(self):
        assert safe_mask("abc") is None
        assert safe_mask("12345") is None
        assert safe_mask("") is None

    def test_six_char_secret_returns_masked(self):
        result = safe_mask("abcdef")
        assert result is not None
        assert "..." in result

    def test_long_secret_shows_partial(self):
        result = safe_mask("sk-abc123xyz789longkey")
        assert result is not None
        assert result.startswith("sk-")
        assert "..." in result

    def test_exactly_threshold(self):
        assert safe_mask("123456") is not None
        assert safe_mask("12345") is None


class TestMaskSecretValue:
    def test_short_value_returns_stars(self):
        assert mask_secret_value("abc") == "******"

    def test_long_value_preserves_ends(self):
        result = mask_secret_value("sk-abc123xyz789")
        assert result[0] == "s"
        assert "..." in result
