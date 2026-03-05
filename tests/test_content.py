"""Tests for content analyzer."""

from mcp_seo.analyzers.content import (
    _count_syllables,
    analyze_content,
    format_content_report,
)
from tests.conftest import BAD_HTML, GOOD_HTML


class TestCountSyllables:
    def test_monosyllabic(self):
        assert _count_syllables("cat") == 1
        assert _count_syllables("the") == 1

    def test_polysyllabic(self):
        assert _count_syllables("beautiful") >= 3
        assert _count_syllables("information") >= 3

    def test_short_word(self):
        assert _count_syllables("a") == 1
        assert _count_syllables("to") == 1


class TestAnalyzeContent:
    def test_good_html_word_count(self):
        result = analyze_content(GOOD_HTML)
        assert result.word_count > 100

    def test_good_html_not_thin(self):
        result = analyze_content(GOOD_HTML)
        # Good HTML has enough content
        thin_issues = [i for i in result.issues if "thin content" in i.lower()]
        assert len(thin_issues) == 0

    def test_good_html_readability(self):
        result = analyze_content(GOOD_HTML)
        assert result.flesch_reading_ease > 0
        assert result.flesch_kincaid_grade > 0
        assert result.readability_level != ""

    def test_good_html_keywords(self):
        result = analyze_content(GOOD_HTML)
        assert len(result.top_keywords) > 0
        # SEO/Python should appear in top keywords
        keyword_words = [w for w, _ in result.top_keywords]
        assert any("seo" in w or "python" in w or "tools" in w for w in keyword_words)

    def test_good_html_keyword_density(self):
        result = analyze_content(GOOD_HTML)
        assert len(result.keyword_density) > 0
        for _word, density in result.keyword_density.items():
            assert 0 < density < 100

    def test_good_html_ngrams(self):
        result = analyze_content(GOOD_HTML)
        assert len(result.top_bigrams) > 0
        assert len(result.top_trigrams) > 0

    def test_good_html_text_html_ratio(self):
        result = analyze_content(GOOD_HTML)
        assert result.text_to_html_ratio > 0

    def test_good_html_reading_time(self):
        result = analyze_content(GOOD_HTML)
        assert result.reading_time_minutes > 0

    def test_bad_html_thin_content(self):
        result = analyze_content(BAD_HTML)
        assert result.word_count < 300
        assert any("thin content" in i.lower() for i in result.issues)

    def test_format_report(self):
        result = analyze_content(GOOD_HTML)
        report = format_content_report(result)
        assert "# Content Analysis" in report
        assert "Flesch" in report
        assert "Readability" in report
