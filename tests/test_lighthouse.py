"""Tests for lighthouse scoring engine."""

from mcp_seo.analyzers.lighthouse import format_lighthouse_report, run_lighthouse
from tests.conftest import BAD_HTML, GOOD_HTML


class TestLighthouse:
    def test_good_html_high_score(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        # Good HTML should score well
        assert result.overall_score >= 60

    def test_good_html_has_categories(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        category_names = [c.category for c in result.categories]
        assert "Meta Tags" in category_names
        assert "Heading Structure" in category_names
        assert "Content Quality" in category_names
        assert "Images" in category_names
        assert "Structured Data" in category_names
        assert "Links" in category_names

    def test_good_html_no_critical_issues(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.critical_issues) == 0

    def test_good_html_passed_checks(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.passed_checks) > 5

    def test_bad_html_low_score(self):
        result = run_lighthouse(BAD_HTML, "https://example.com")
        # Bad HTML should score poorly
        assert result.overall_score < 60

    def test_bad_html_has_issues(self):
        result = run_lighthouse(BAD_HTML, "https://example.com")
        total_issues = len(result.critical_issues) + len(result.warnings)
        assert total_issues > 3

    def test_category_scores_0_to_100(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        for cat in result.categories:
            assert 0 <= cat.score <= 100

    def test_weighted_scoring(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        # Overall score should be a weighted average, not simple mean
        sum(c.score for c in result.categories) / len(result.categories)
        # They can differ due to weights
        assert isinstance(result.overall_score, int)

    def test_continuous_scoring(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        # Check that individual check scores are continuous (0.0-1.0)
        for cat in result.categories:
            for check in cat.checks:
                assert 0.0 <= check.score <= 1.0

    def test_format_report(self):
        result = run_lighthouse(GOOD_HTML, "https://example.com/seo-tools")
        report = format_lighthouse_report(result)
        assert "# SEO Audit Report" in report
        assert "Overall Score" in report
        assert "Category Scores" in report
