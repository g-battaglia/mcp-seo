"""Tests for headings analyzer."""

from mcp_seo.analyzers.headings import analyze_headings, format_headings_report
from tests.conftest import BAD_HTML, GOOD_HTML


class TestAnalyzeHeadings:
    def test_good_html_single_h1(self):
        result = analyze_headings(GOOD_HTML)
        assert result.h1_count == 1
        assert result.hierarchy_valid is True

    def test_good_html_has_headings(self):
        result = analyze_headings(GOOD_HTML)
        assert result.total_count >= 3

    def test_good_html_correct_hierarchy(self):
        result = analyze_headings(GOOD_HTML)
        # h1 -> h2 -> h3 -- no skips
        assert result.hierarchy_valid is True

    def test_good_html_heading_order(self):
        result = analyze_headings(GOOD_HTML)
        # First heading should be h1
        assert result.headings[0].level == 1

    def test_bad_html_no_h1(self):
        result = analyze_headings(BAD_HTML)
        assert result.h1_count == 0
        assert result.hierarchy_valid is False
        assert any("no <h1>" in i.lower() for i in result.issues)

    def test_bad_html_skipped_levels(self):
        result = analyze_headings(BAD_HTML)
        # h2 -> h4 skips h3
        assert any("skipped" in i.lower() for i in result.issues)

    def test_bad_html_duplicate_headings(self):
        result = analyze_headings(BAD_HTML)
        # "Skipped H1" appears twice
        assert len(result.duplicate_headings) > 0

    def test_heading_length_tracking(self):
        result = analyze_headings(GOOD_HTML)
        for h in result.headings:
            assert h.length == len(h.text)
            assert h.length > 0

    def test_format_report(self):
        result = analyze_headings(GOOD_HTML)
        report = format_headings_report(result)
        assert "# Heading Hierarchy Analysis" in report
        assert "h1" in report.lower()
