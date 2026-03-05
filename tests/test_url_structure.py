"""Tests for URL structure analyzer."""

from mcp_seo.analyzers.url_structure import analyze_url_structure, format_url_structure_report


class TestAnalyzeUrlStructure:
    def test_basic_url(self):
        result = analyze_url_structure("https://example.com/blog/post")
        assert result.scheme == "https"
        assert result.netloc == "example.com"
        assert result.depth == 2
        assert result.full_length == len("https://example.com/blog/post")

    def test_root_url(self):
        result = analyze_url_structure("https://example.com/")
        assert result.depth == 0
        # Root path "/" is not flagged as trailing slash (only paths like /foo/ are)
        assert not result.has_trailing_slash

    def test_deep_url(self):
        result = analyze_url_structure("https://example.com/a/b/c/d/e")
        assert result.depth == 5
        assert any("depth" in i.lower() for i in result.issues)

    def test_underscores_flagged(self):
        result = analyze_url_structure("https://example.com/my_page")
        assert result.uses_underscores
        assert any("underscore" in i.lower() for i in result.issues)

    def test_hyphens_ok(self):
        result = analyze_url_structure("https://example.com/my-page")
        assert result.uses_hyphens
        assert not result.uses_underscores

    def test_uppercase_flagged(self):
        result = analyze_url_structure("https://example.com/MyPage")
        assert result.has_uppercase
        assert any("uppercase" in i.lower() for i in result.issues)

    def test_tracking_params_detected(self):
        result = analyze_url_structure("https://example.com/page?utm_source=google&utm_medium=cpc")
        assert result.has_tracking_params
        assert "utm_source" in result.tracking_params_found
        assert "utm_medium" in result.tracking_params_found
        assert result.has_query_params
        assert result.query_param_count == 2

    def test_session_id_detected(self):
        result = analyze_url_structure("https://example.com/page?phpsessid=abc123")
        assert result.has_session_id
        assert any("CRITICAL" in i for i in result.issues)

    def test_file_extension_detected(self):
        result = analyze_url_structure("https://example.com/page.php")
        assert result.has_file_extension
        assert result.file_extension == ".php"
        assert any(".php" in i for i in result.issues)

    def test_clean_url_no_extension(self):
        result = analyze_url_structure("https://example.com/about")
        assert not result.has_file_extension
        assert result.file_extension is None

    def test_path_keywords_extracted(self):
        result = analyze_url_structure("https://example.com/python-seo-tools")
        assert "python" in result.path_keywords
        assert "seo" in result.path_keywords
        assert "tools" in result.path_keywords

    def test_long_url_flagged(self):
        long_path = "/very-long-path-segment/" * 5
        result = analyze_url_structure(f"https://example.com{long_path}")
        assert any("long" in i.lower() for i in result.issues)

    def test_format_report(self):
        result = analyze_url_structure("https://example.com/blog/post")
        report = format_url_structure_report(result)
        assert "# URL Structure Analysis" in report
        assert "example.com" in report
