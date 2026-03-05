"""Tests for utility functions."""

import pytest

from mcp_seo.utils import clear_soup_cache, ensure_url, parse_html, parse_html_fresh


class TestEnsureUrl:
    def test_adds_https(self):
        assert ensure_url("example.com") == "https://example.com"

    def test_preserves_https(self):
        assert ensure_url("https://example.com") == "https://example.com"

    def test_preserves_http(self):
        assert ensure_url("http://example.com") == "http://example.com"

    def test_with_path(self):
        assert ensure_url("example.com/path") == "https://example.com/path"

    def test_strips_whitespace(self):
        assert ensure_url("  example.com  ") == "https://example.com"

    def test_blocks_file_scheme(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("file:///etc/passwd")

    def test_blocks_javascript_scheme(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("javascript:alert(1)")

    def test_blocks_data_scheme(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("data:text/html,<h1>hi</h1>")

    def test_blocks_blob_scheme(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("blob:https://example.com/uuid")

    def test_blocks_vbscript_scheme(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("vbscript:MsgBox")

    def test_blocks_ftp_scheme(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("ftp://example.com/file")

    def test_blocks_case_insensitive(self):
        with pytest.raises(ValueError, match="Blocked URL scheme"):
            ensure_url("FILE:///etc/passwd")


class TestParseHtml:
    def test_returns_soup(self):
        soup = parse_html("<html><body><p>Hello</p></body></html>")
        assert soup.find("p").get_text() == "Hello"

    def test_caching_same_content(self):
        html = "<html><body><p>Test</p></body></html>"
        soup1 = parse_html(html)
        soup2 = parse_html(html)
        # Same content string should return same cached soup
        assert soup1 is soup2

    def test_caching_different_objects_same_content(self):
        # Two different string objects with same content should hit cache
        html1 = "<html><body><p>Cache</p></body></html>"
        html2 = "<html>" + "<body><p>Cache</p></body></html>"
        soup1 = parse_html(html1)
        soup2 = parse_html(html2)
        assert soup1 is soup2

    def test_fresh_parse(self):
        html = "<html><body><p>Test</p></body></html>"
        soup1 = parse_html_fresh(html)
        soup2 = parse_html_fresh(html)
        # Fresh parses should return different objects
        assert soup1 is not soup2

    def test_clear_cache(self):
        html = "<html><body><p>Test</p></body></html>"
        soup1 = parse_html(html)
        clear_soup_cache()
        soup2 = parse_html(html)
        # After clear, should be a new parse (different object)
        assert soup1 is not soup2
