"""Tests for HTTP headers analyzer."""

from mcp_seo.analyzers.headers import analyze_headers, format_headers_report


class TestAnalyzeHeaders:
    def test_basic_headers(self):
        headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "max-age=3600",
            "Content-Encoding": "gzip",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        result = analyze_headers(headers, 200, [])
        assert result.status_code == 200
        assert result.cache_control == "max-age=3600"
        assert result.content_encoding == "gzip"
        assert result.hsts_max_age == 31536000

    def test_missing_security_headers(self):
        result = analyze_headers({}, 200, [])
        assert any("HSTS" in i for i in result.issues)
        assert any("Cache-Control" in i for i in result.issues)

    def test_hsts_max_age_too_low(self):
        headers = {"Strict-Transport-Security": "max-age=3600"}
        result = analyze_headers(headers, 200, [])
        assert result.hsts_max_age == 3600
        assert any("max-age too low" in i for i in result.issues)

    def test_server_info_leak(self):
        headers = {"Server": "Apache/2.4.41", "X-Powered-By": "PHP/7.4"}
        result = analyze_headers(headers, 200, [])
        assert any("Server header" in i for i in result.issues)
        assert any("X-Powered-By" in i for i in result.issues)

    def test_long_redirect_chain(self):
        result = analyze_headers({}, 200, ["url1", "url2", "url3"])
        assert any("redirect chain" in i.lower() for i in result.issues)

    def test_ssl_error(self):
        result = analyze_headers({}, 200, [], ssl_valid=False, ssl_error="cert expired")
        assert not result.ssl_valid
        assert any("SSL" in i for i in result.issues)

    def test_cookie_security(self):
        headers = {"Set-Cookie": "session=abc123; Path=/"}
        result = analyze_headers(headers, 200, [])
        assert result.has_cookies is True
        assert any("Secure" in i for i in result.cookie_issues)

    def test_temporary_redirect(self):
        result = analyze_headers({}, 302, ["https://old.com"])
        assert any("temporary redirect" in i.lower() for i in result.issues)

    def test_error_status_code(self):
        result = analyze_headers({}, 404, [])
        assert any("404" in i for i in result.issues)

    def test_format_report(self):
        result = analyze_headers({"Content-Type": "text/html"}, 200, [])
        report = format_headers_report(result)
        assert "# HTTP Headers Analysis" in report
        assert "200" in report
