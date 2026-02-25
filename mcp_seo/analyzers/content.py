"""Content analysis: word count, readability, keyword density."""

from __future__ import annotations

import re
from collections import Counter

from bs4 import BeautifulSoup
from pydantic import BaseModel


class ContentAnalysis(BaseModel):
    word_count: int = 0
    char_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_sentence_length: float = 0
    avg_word_length: float = 0
    reading_time_minutes: float = 0
    top_keywords: list[tuple[str, int]] = []
    top_bigrams: list[tuple[str, int]] = []
    top_trigrams: list[tuple[str, int]] = []
    text_to_html_ratio: float = 0
    issues: list[str] = []


# Common stop words to exclude from keyword analysis
STOP_WORDS = set("""
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further get
got had hadn't has hasn't have haven't having he he'd he'll he's her here
here's hers herself him himself his how how's i i'd i'll i'm i've if in into
is isn't it it's its itself let's me more most mustn't my myself no nor not of
off on once only or other ought our ours ourselves out over own same shan't she
she'd she'll she's should shouldn't so some such than that that's the their
theirs them themselves then there there's these they they'd they'll they're
they've this those through to too under until up us very was wasn't we we'd
we'll we're we've were weren't what what's when when's where where's which
while who who's whom why why's will with won't would wouldn't you you'd you'll
you're you've your yours yourself yourselves the a an is was were are been be
have has had do does did will would shall should may might can could
""".split())


def _extract_text(html: str) -> str:
    """Extract visible text from HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_words(text: str) -> list[str]:
    """Get cleaned word list."""
    words = re.findall(r"[a-zA-ZÀ-ÿ]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOP_WORDS]


def _get_ngrams(words: list[str], n: int) -> list[tuple[str, int]]:
    """Get top n-grams."""
    ngrams = [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]
    return Counter(ngrams).most_common(10)


def analyze_content(html: str) -> ContentAnalysis:
    """Analyze page content for SEO."""
    result = ContentAnalysis()
    issues: list[str] = []

    text = _extract_text(html)
    html_size = len(html)
    text_size = len(text)

    # Basic metrics
    all_words = text.split()
    result.word_count = len(all_words)
    result.char_count = len(text)

    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    result.sentence_count = len(sentences)

    soup = BeautifulSoup(html, "lxml")
    result.paragraph_count = len(soup.find_all("p"))

    if result.sentence_count > 0:
        result.avg_sentence_length = round(result.word_count / result.sentence_count, 1)

    if result.word_count > 0:
        result.avg_word_length = round(
            sum(len(w) for w in all_words) / len(all_words), 1
        )

    # Reading time (avg 200 wpm)
    result.reading_time_minutes = round(result.word_count / 200, 1)

    # Text-to-HTML ratio
    if html_size > 0:
        result.text_to_html_ratio = round((text_size / html_size) * 100, 1)

    # Keyword analysis
    words = _get_words(text)
    result.top_keywords = Counter(words).most_common(15)
    result.top_bigrams = _get_ngrams(words, 2)
    result.top_trigrams = _get_ngrams(words, 3)

    # Issues
    if result.word_count < 300:
        issues.append(f"Thin content: {result.word_count} words (recommended 300+)")
    if result.text_to_html_ratio < 10:
        issues.append(f"Low text-to-HTML ratio: {result.text_to_html_ratio}% (recommended 10%+)")
    if result.avg_sentence_length > 25:
        issues.append(f"Long average sentence length: {result.avg_sentence_length} words")

    result.issues = issues
    return result


def format_content_report(analysis: ContentAnalysis) -> str:
    """Format content analysis as a readable report."""
    lines = ["# Content Analysis", ""]

    lines.append("## Text Metrics")
    lines.append(f"- **Word Count**: {analysis.word_count}")
    lines.append(f"- **Character Count**: {analysis.char_count}")
    lines.append(f"- **Sentences**: {analysis.sentence_count}")
    lines.append(f"- **Paragraphs**: {analysis.paragraph_count}")
    lines.append(f"- **Avg Sentence Length**: {analysis.avg_sentence_length} words")
    lines.append(f"- **Avg Word Length**: {analysis.avg_word_length} chars")
    lines.append(f"- **Reading Time**: {analysis.reading_time_minutes} min")
    lines.append(f"- **Text/HTML Ratio**: {analysis.text_to_html_ratio}%")
    lines.append("")

    if analysis.top_keywords:
        lines.append("## Top Keywords")
        for word, count in analysis.top_keywords:
            lines.append(f"- **{word}**: {count}")
        lines.append("")

    if analysis.top_bigrams:
        lines.append("## Top Bigrams")
        for bigram, count in analysis.top_bigrams:
            lines.append(f"- **{bigram}**: {count}")
        lines.append("")

    if analysis.top_trigrams:
        lines.append("## Top Trigrams")
        for trigram, count in analysis.top_trigrams:
            lines.append(f"- **{trigram}**: {count}")
        lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
