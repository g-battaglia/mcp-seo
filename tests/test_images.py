"""Tests for images analyzer."""

from mcp_seo.analyzers.images import analyze_images, format_images_report
from tests.conftest import BAD_HTML, GOOD_HTML


class TestAnalyzeImages:
    def test_good_html_finds_images(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        assert result.total_images == 2

    def test_good_html_alt_text(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        assert result.images_with_alt == 2
        assert result.images_without_alt == 0

    def test_good_html_lazy_loading(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        assert result.images_lazy_loaded == 2

    def test_good_html_dimensions(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        assert result.images_with_dimensions == 2

    def test_good_html_modern_formats(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        assert result.modern_format_count == 2  # webp + avif
        assert result.legacy_format_count == 0

    def test_good_html_format_detection(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        formats = [img.format for img in result.images]
        assert "webp" in formats
        assert "avif" in formats

    def test_bad_html_missing_alt(self):
        result = analyze_images(BAD_HTML, "https://example.com")
        assert result.images_without_alt == 2
        assert any("missing alt" in i.lower() for i in result.issues)

    def test_bad_html_legacy_formats(self):
        result = analyze_images(BAD_HTML, "https://example.com")
        assert result.legacy_format_count > 0

    def test_bad_html_no_lazy_loading(self):
        result = analyze_images(BAD_HTML, "https://example.com")
        assert result.images_lazy_loaded == 0

    def test_bad_html_no_dimensions(self):
        result = analyze_images(BAD_HTML, "https://example.com")
        assert result.images_with_dimensions == 0

    def test_format_report(self):
        result = analyze_images(GOOD_HTML, "https://example.com/seo-tools")
        report = format_images_report(result)
        assert "# Image Analysis" in report
