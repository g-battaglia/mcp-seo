"""Tests for accessibility analyzer."""

from mcp_seo.analyzers.accessibility import analyze_accessibility, format_accessibility_report

ACCESSIBLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Accessible Page</title></head>
<body>
    <a href="#main-content">Skip to main content</a>
    <header><nav><a href="/">Home</a></nav></header>
    <main id="main-content">
        <h1>Accessible Page</h1>
        <p>Content here.</p>
        <img src="/photo.jpg" alt="A descriptive alt text">
        <form>
            <label for="email">Email</label>
            <input type="text" id="email" name="email">
        </form>
        <table>
            <caption>Data Table</caption>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>A</td><td>1</td></tr>
        </table>
    </main>
    <footer><p>Footer content</p></footer>
</body>
</html>"""


INACCESSIBLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Bad Page</title></head>
<body>
    <div>
        <h1>No landmarks here</h1>
        <img src="/no-alt.jpg">
        <img src="/also-no-alt.png">
        <a href="/empty-link"></a>
        <form>
            <input type="text" name="query">
        </form>
        <table>
            <tr><td>No headers</td><td>Bad</td></tr>
        </table>
    </div>
</body>
</html>"""


class TestAnalyzeAccessibility:
    def test_accessible_page_high_score(self):
        result = analyze_accessibility(ACCESSIBLE_HTML)
        assert result.score >= 80
        assert result.has_lang_attribute
        assert result.lang_value == "en"
        assert result.has_main_landmark
        assert result.has_nav_landmark
        assert result.has_banner_landmark
        assert result.has_contentinfo_landmark
        assert result.has_skip_nav

    def test_images_with_alt(self):
        result = analyze_accessibility(ACCESSIBLE_HTML)
        assert result.images_total == 1
        assert result.images_with_alt == 1
        assert result.images_missing_alt == 0

    def test_form_labels(self):
        result = analyze_accessibility(ACCESSIBLE_HTML)
        assert result.form_inputs_total == 1
        assert result.form_inputs_with_label == 1
        assert result.form_inputs_without_label == 0

    def test_table_headers(self):
        result = analyze_accessibility(ACCESSIBLE_HTML)
        assert result.tables_total == 1
        assert result.tables_with_headers == 1
        assert result.tables_with_caption == 1

    def test_inaccessible_page_low_score(self):
        result = analyze_accessibility(INACCESSIBLE_HTML)
        assert result.score < 50
        assert not result.has_lang_attribute
        assert not result.has_skip_nav

    def test_missing_alt_detected(self):
        result = analyze_accessibility(INACCESSIBLE_HTML)
        assert result.images_missing_alt == 2
        assert any("CRITICAL" in i and "alt" in i.lower() for i in result.issues)

    def test_missing_lang_detected(self):
        result = analyze_accessibility(INACCESSIBLE_HTML)
        assert any("CRITICAL" in i and "lang" in i.lower() for i in result.issues)

    def test_links_without_text(self):
        result = analyze_accessibility(INACCESSIBLE_HTML)
        assert result.links_without_text > 0
        assert any("link" in i.lower() and "text" in i.lower() for i in result.issues)

    def test_form_without_label(self):
        result = analyze_accessibility(INACCESSIBLE_HTML)
        assert result.form_inputs_without_label > 0
        assert any("label" in i.lower() for i in result.issues)

    def test_table_without_headers(self):
        result = analyze_accessibility(INACCESSIBLE_HTML)
        assert result.tables_total == 1
        assert result.tables_with_headers == 0
        assert any("header" in i.lower() for i in result.issues)

    def test_format_report(self):
        result = analyze_accessibility(ACCESSIBLE_HTML)
        report = format_accessibility_report(result)
        assert "# Accessibility Analysis" in report
        assert "Score" in report


class TestAccessibilitySkipNav:
    def test_skip_nav_variants(self):
        html = """<html lang="en"><body>
            <a href="#content">Jump to main content</a>
            <main id="content"><p>Hello</p></main>
        </body></html>"""
        result = analyze_accessibility(html)
        assert result.has_skip_nav

    def test_no_skip_nav(self):
        html = """<html lang="en"><body>
            <a href="/about">About</a>
            <main><p>Hello</p></main>
        </body></html>"""
        result = analyze_accessibility(html)
        assert not result.has_skip_nav
