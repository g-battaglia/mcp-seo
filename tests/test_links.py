"""Tests for links analyzer."""

from mcp_seo.analyzers.links import analyze_links, format_links_report
from tests.conftest import BAD_HTML, GOOD_HTML


class TestAnalyzeLinks:
    def test_good_html_finds_links(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert result.total_links > 0

    def test_good_html_internal_links(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.internal_links) > 0

    def test_good_html_external_links(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.external_links) > 0

    def test_good_html_nofollow_detection(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.nofollow_links) > 0

    def test_good_html_sponsored_detection(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.sponsored_links) > 0

    def test_good_html_pagination(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert result.has_pagination is True
        assert result.next_page is not None

    def test_good_html_follow_ratio(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert 0 <= result.follow_ratio <= 100

    def test_good_html_internal_ratio(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        assert result.internal_ratio > 0

    def test_bad_html_links_without_text(self):
        result = analyze_links(BAD_HTML, "https://example.com")
        assert len(result.links_without_text) > 0
        assert any("without anchor text" in i for i in result.issues)

    def test_url_resolution(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        for link in result.internal_links:
            assert link.href.startswith("https://")

    def test_format_report(self):
        result = analyze_links(GOOD_HTML, "https://example.com/seo-tools")
        report = format_links_report(result)
        assert "# Link Analysis" in report
        assert "Internal" in report
