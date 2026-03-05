"""Tests for crawler _normalize_url() function."""

from mcp_seo.crawler import _normalize_url


class TestNormalizeUrl:
    def test_basic_url_unchanged(self):
        assert _normalize_url("https://example.com/page") == "https://example.com/page"

    def test_strips_trailing_slash(self):
        assert _normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_preserves_root_slash(self):
        # Root URL should keep its trailing slash (it's the root path, not a trailing slash)
        result = _normalize_url("https://example.com/")
        assert result == "https://example.com/"

    def test_strips_fragment(self):
        assert _normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_strips_utm_source(self):
        result = _normalize_url("https://example.com/page?utm_source=google")
        assert result == "https://example.com/page"

    def test_strips_utm_medium(self):
        result = _normalize_url("https://example.com/page?utm_medium=cpc")
        assert result == "https://example.com/page"

    def test_strips_utm_campaign(self):
        result = _normalize_url("https://example.com/page?utm_campaign=spring")
        assert result == "https://example.com/page"

    def test_strips_fbclid(self):
        result = _normalize_url("https://example.com/page?fbclid=abc123")
        assert result == "https://example.com/page"

    def test_strips_gclid(self):
        result = _normalize_url("https://example.com/page?gclid=def456")
        assert result == "https://example.com/page"

    def test_strips_session_params(self):
        result = _normalize_url("https://example.com/page?phpsessid=abc&sid=def")
        assert result == "https://example.com/page"

    def test_preserves_non_tracking_params(self):
        result = _normalize_url("https://example.com/search?q=python&page=2")
        assert "q=python" in result
        assert "page=2" in result

    def test_mixed_params(self):
        result = _normalize_url("https://example.com/page?id=5&utm_source=google&lang=en")
        assert "id=5" in result
        assert "lang=en" in result
        assert "utm_source" not in result

    def test_strips_ga_params(self):
        result = _normalize_url("https://example.com/page?_ga=1.2.3&_gl=x.y")
        assert result == "https://example.com/page"

    def test_all_params_stripped(self):
        result = _normalize_url("https://example.com/page?utm_source=a&fbclid=b")
        # All tracking params removed, no query string left
        assert "?" not in result

    def test_complex_url(self):
        url = "https://example.com/blog/post/?utm_source=google&utm_medium=cpc&ref=twitter#comments"
        result = _normalize_url(url)
        assert result == "https://example.com/blog/post"
