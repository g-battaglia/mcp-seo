"""Tests for structured data analyzer."""

from mcp_seo.analyzers.structured_data import (
    analyze_structured_data,
    format_structured_data_report,
)
from tests.conftest import BAD_HTML, GOOD_HTML, STRUCTURED_DATA_HTML


class TestAnalyzeStructuredData:
    def test_good_html_has_jsonld(self):
        result = analyze_structured_data(GOOD_HTML)
        assert result.json_ld_count > 0

    def test_good_html_article_type(self):
        result = analyze_structured_data(GOOD_HTML)
        assert "Article" in result.schema_types

    def test_good_html_valid(self):
        result = analyze_structured_data(GOOD_HTML)
        assert all(item.valid for item in result.items)

    def test_structured_data_product(self):
        result = analyze_structured_data(STRUCTURED_DATA_HTML)
        assert "Product" in result.schema_types

    def test_structured_data_breadcrumb(self):
        result = analyze_structured_data(STRUCTURED_DATA_HTML)
        assert "BreadcrumbList" in result.schema_types
        assert result.has_breadcrumb is True

    def test_structured_data_invalid_json(self):
        result = analyze_structured_data(STRUCTURED_DATA_HTML)
        invalid = [i for i in result.items if not i.valid]
        assert len(invalid) > 0
        assert any("Invalid JSON" in e for i in invalid for e in i.errors)

    def test_structured_data_microdata(self):
        result = analyze_structured_data(STRUCTURED_DATA_HTML)
        assert result.microdata_count > 0
        assert "Organization" in result.schema_types

    def test_rich_result_detection(self):
        result = analyze_structured_data(GOOD_HTML)
        assert len(result.rich_result_types) > 0

    def test_missing_properties_detection(self):
        # Product without required properties like "offers"
        result = analyze_structured_data(STRUCTURED_DATA_HTML)
        # Product has name and image, which are the required ones
        product_items = [i for i in result.items if i.type == "Product"]
        assert len(product_items) > 0

    def test_no_structured_data(self):
        result = analyze_structured_data(BAD_HTML)
        assert result.total_items == 0
        assert any("no structured data" in i.lower() for i in result.issues)

    def test_format_report(self):
        result = analyze_structured_data(GOOD_HTML)
        report = format_structured_data_report(result)
        assert "# Structured Data Analysis" in report
        assert "Article" in report
