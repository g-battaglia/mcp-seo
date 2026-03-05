"""Tests for meta tags analyzer."""

from mcp_seo.analyzers.meta import analyze_meta, format_meta_report
from tests.conftest import BAD_HTML, GOOD_HTML


class TestAnalyzeMeta:
    def test_good_html_extracts_title(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.title is not None
        assert "Python SEO Tools" in result.title
        assert 30 <= result.title_length <= 60

    def test_good_html_extracts_description(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.description is not None
        assert 70 <= result.description_length <= 160

    def test_good_html_has_canonical(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.canonical == "https://example.com/seo-tools"
        assert result.canonical_is_self is True

    def test_good_html_has_viewport(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.viewport is not None
        assert "width=device-width" in result.viewport

    def test_good_html_has_charset(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.charset is not None

    def test_good_html_has_language(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.language == "en"

    def test_good_html_has_og_tags(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert "og:title" in result.og_tags
        assert "og:description" in result.og_tags
        assert "og:image" in result.og_tags
        assert "og:url" in result.og_tags

    def test_good_html_has_twitter_tags(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert "twitter:card" in result.twitter_tags

    def test_good_html_has_hreflang(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert len(result.hreflang_tags) == 3
        langs = [h.lang for h in result.hreflang_tags]
        assert "x-default" in langs
        assert "en" in langs
        assert "it" in langs

    def test_good_html_has_favicon(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.favicon is not None

    def test_good_html_pixel_width(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        assert result.title_pixel_width > 0
        assert result.description_pixel_width > 0

    def test_bad_html_short_title(self):
        result = analyze_meta(BAD_HTML, "https://example.com")
        assert result.title == "Hi"
        assert result.title_length < 30
        assert any("too short" in i.lower() for i in result.issues)

    def test_bad_html_missing_description(self):
        result = analyze_meta(BAD_HTML, "https://example.com")
        assert result.description is None
        assert any("missing meta description" in i.lower() for i in result.issues)

    def test_bad_html_missing_viewport(self):
        result = analyze_meta(BAD_HTML, "https://example.com")
        assert result.viewport is None
        assert any("viewport" in i.lower() for i in result.issues)

    def test_bad_html_missing_canonical(self):
        result = analyze_meta(BAD_HTML, "https://example.com")
        assert result.canonical is None

    def test_bad_html_missing_lang(self):
        result = analyze_meta(BAD_HTML, "https://example.com")
        assert result.language is None

    def test_bad_html_no_og_tags(self):
        result = analyze_meta(BAD_HTML, "https://example.com")
        assert len(result.og_tags) == 0

    def test_format_report_returns_string(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        report = format_meta_report(result)
        assert isinstance(report, str)
        assert "# Meta Tags Analysis" in report

    def test_good_html_few_issues(self):
        result = analyze_meta(GOOD_HTML, "https://example.com/seo-tools")
        # Good HTML should have very few critical issues
        critical = [i for i in result.issues if "CRITICAL" in i]
        assert len(critical) == 0
