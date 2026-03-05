"""Content analysis: word count, readability (Flesch-Kincaid), keyword density, n-grams."""

from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel

from mcp_seo.utils import get_logger, parse_html_fresh

logger = get_logger("content")


class ContentAnalysis(BaseModel):
    word_count: int = 0
    char_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_sentence_length: float = 0
    avg_word_length: float = 0
    reading_time_minutes: float = 0

    # Readability scores
    flesch_reading_ease: float = 0
    flesch_kincaid_grade: float = 0
    readability_level: str = ""

    # Keyword analysis
    top_keywords: list[tuple[str, int]] = []
    keyword_density: dict[str, float] = {}  # word -> percentage
    top_bigrams: list[tuple[str, int]] = []
    top_trigrams: list[tuple[str, int]] = []

    text_to_html_ratio: float = 0
    issues: list[str] = []


# ── Stop words (English + common European) ───────────────────

STOP_WORDS_EN = set(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "aren't",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can't",
        "cannot",
        "could",
        "couldn't",
        "did",
        "didn't",
        "do",
        "does",
        "doesn't",
        "doing",
        "don't",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "get",
        "got",
        "had",
        "hadn't",
        "has",
        "hasn't",
        "have",
        "haven't",
        "having",
        "he",
        "he'd",
        "he'll",
        "he's",
        "her",
        "here",
        "here's",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "how's",
        "i",
        "i'd",
        "i'll",
        "i'm",
        "i've",
        "if",
        "in",
        "into",
        "is",
        "isn't",
        "it",
        "it's",
        "its",
        "itself",
        "let's",
        "me",
        "more",
        "most",
        "mustn't",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "ought",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "shan't",
        "she",
        "she'd",
        "she'll",
        "she's",
        "should",
        "shouldn't",
        "so",
        "some",
        "such",
        "than",
        "that",
        "that's",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "there's",
        "these",
        "they",
        "they'd",
        "they'll",
        "they're",
        "they've",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "us",
        "very",
        "was",
        "wasn't",
        "we",
        "we'd",
        "we'll",
        "we're",
        "we've",
        "were",
        "weren't",
        "what",
        "what's",
        "when",
        "when's",
        "where",
        "where's",
        "which",
        "while",
        "who",
        "who's",
        "whom",
        "why",
        "why's",
        "will",
        "with",
        "won't",
        "would",
        "wouldn't",
        "you",
        "you'd",
        "you'll",
        "you're",
        "you've",
        "your",
        "yours",
        "yourself",
        "yourselves",
        "the",
        "a",
        "an",
        "is",
        "was",
        "were",
        "are",
        "been",
        "be",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "can",
        "could",
        "also",
        "just",
        "like",
        "even",
        "still",
        "already",
        "really",
        "much",
        "many",
        "get",
        "got",
        "one",
        "two",
        "three",
        "use",
        "used",
        "new",
        "make",
        "made",
        "know",
        "going",
        "way",
        "come",
        "back",
        "well",
        "also",
    ]
)

STOP_WORDS_IT = set(
    [
        "il",
        "lo",
        "la",
        "i",
        "gli",
        "le",
        "un",
        "uno",
        "una",
        "di",
        "del",
        "dello",
        "della",
        "dei",
        "degli",
        "delle",
        "in",
        "con",
        "su",
        "per",
        "tra",
        "fra",
        "da",
        "a",
        "al",
        "allo",
        "alla",
        "ai",
        "agli",
        "alle",
        "che",
        "chi",
        "cui",
        "non",
        "è",
        "sono",
        "era",
        "erano",
        "si",
        "no",
        "sì",
        "come",
        "quando",
        "anche",
        "più",
        "già",
        "mai",
        "ancora",
        "molto",
        "poco",
        "tutto",
        "tutti",
        "questa",
        "questo",
        "queste",
        "questi",
        "quale",
        "quali",
        "dove",
        "perché",
        "cosa",
        "se",
        "ma",
        "ed",
        "o",
        "né",
        "ho",
        "ha",
        "hanno",
        "fare",
        "fatto",
        "essere",
        "stato",
        "stata",
        "stati",
        "state",
        "suo",
        "sua",
        "suoi",
        "sue",
    ]
)

STOP_WORDS_ES = set(
    [
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "y",
        "o",
        "pero",
        "si",
        "no",
        "por",
        "para",
        "con",
        "en",
        "que",
        "es",
        "son",
        "era",
        "como",
        "más",
        "muy",
        "también",
        "ya",
        "esta",
        "este",
        "estos",
        "estas",
        "todo",
        "todos",
    ]
)

STOP_WORDS_FR = set(
    [
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "au",
        "aux",
        "et",
        "ou",
        "mais",
        "si",
        "en",
        "que",
        "qui",
        "est",
        "sont",
        "pas",
        "ne",
        "plus",
        "avec",
        "pour",
        "dans",
        "sur",
        "par",
        "tout",
        "tous",
        "cette",
        "ces",
        "très",
        "aussi",
    ]
)

STOP_WORDS_DE = set(
    [
        "der",
        "die",
        "das",
        "ein",
        "eine",
        "einer",
        "eines",
        "dem",
        "den",
        "des",
        "und",
        "oder",
        "aber",
        "wenn",
        "nicht",
        "ist",
        "sind",
        "war",
        "zu",
        "in",
        "von",
        "mit",
        "auf",
        "für",
        "nach",
        "über",
        "auch",
        "wie",
        "noch",
        "aus",
    ]
)

ALL_STOP_WORDS = STOP_WORDS_EN | STOP_WORDS_IT | STOP_WORDS_ES | STOP_WORDS_FR | STOP_WORDS_DE


# ── Syllable counting ────────────────────────────────────────


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a word (English heuristic)."""
    word = word.lower().strip()
    if len(word) <= 3:
        return 1

    # Remove trailing 'e'
    if word.endswith("e"):
        word = word[:-1]

    # Count vowel groups
    count = len(re.findall(r"[aeiouy]+", word))
    return max(count, 1)


# ── Text extraction ──────────────────────────────────────────


def _extract_text(html: str) -> str:
    """Extract visible text from HTML, removing boilerplate."""
    soup = parse_html_fresh(html)

    # Remove script, style, and boilerplate elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        element.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_words(text: str) -> list[str]:
    """Get cleaned word list."""
    words = re.findall(r"[a-zA-ZÀ-ÿ]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in ALL_STOP_WORDS]


def _get_ngrams(words: list[str], n: int) -> list[tuple[str, int]]:
    """Get top n-grams."""
    ngrams = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
    return Counter(ngrams).most_common(10)


# ── Readability scoring ──────────────────────────────────────


def _flesch_reading_ease(total_words: int, total_sentences: int, total_syllables: int) -> float:
    """Calculate Flesch Reading Ease score (0-100, higher = easier)."""
    if total_sentences == 0 or total_words == 0:
        return 0
    return round(
        206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words),
        1,
    )


def _flesch_kincaid_grade(total_words: int, total_sentences: int, total_syllables: int) -> float:
    """Calculate Flesch-Kincaid Grade Level (US school grade)."""
    if total_sentences == 0 or total_words == 0:
        return 0
    return round(
        0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59,
        1,
    )


def _readability_label(fre: float) -> str:
    """Human-readable label for Flesch Reading Ease score."""
    if fre >= 90:
        return "Very Easy (5th grade)"
    elif fre >= 80:
        return "Easy (6th grade)"
    elif fre >= 70:
        return "Fairly Easy (7th grade)"
    elif fre >= 60:
        return "Standard (8th-9th grade)"
    elif fre >= 50:
        return "Fairly Difficult (10th-12th grade)"
    elif fre >= 30:
        return "Difficult (college level)"
    else:
        return "Very Difficult (graduate level)"


# ── Main analyzer ────────────────────────────────────────────


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
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    result.sentence_count = len(sentences)

    soup = parse_html_fresh(html)
    result.paragraph_count = len(soup.find_all("p"))

    if result.sentence_count > 0:
        result.avg_sentence_length = round(result.word_count / result.sentence_count, 1)

    if result.word_count > 0:
        result.avg_word_length = round(sum(len(w) for w in all_words) / len(all_words), 1)

    # Reading time (avg 200 wpm)
    result.reading_time_minutes = round(result.word_count / 200, 1)

    # Text-to-HTML ratio
    if html_size > 0:
        result.text_to_html_ratio = round((text_size / html_size) * 100, 1)

    # Readability scores
    total_syllables = sum(_count_syllables(w) for w in all_words)
    result.flesch_reading_ease = _flesch_reading_ease(result.word_count, result.sentence_count, total_syllables)
    result.flesch_kincaid_grade = _flesch_kincaid_grade(result.word_count, result.sentence_count, total_syllables)
    result.readability_level = _readability_label(result.flesch_reading_ease)

    # Keyword analysis
    words = _get_words(text)
    keyword_counts = Counter(words).most_common(15)
    result.top_keywords = keyword_counts

    # Keyword density (as percentage of total words)
    if result.word_count > 0:
        result.keyword_density = {
            word: round((count / result.word_count) * 100, 2) for word, count in keyword_counts[:10]
        }

    result.top_bigrams = _get_ngrams(words, 2)
    result.top_trigrams = _get_ngrams(words, 3)

    # Issues
    if result.word_count < 300:
        issues.append(f"Thin content: {result.word_count} words (recommended 300+)")
    if result.text_to_html_ratio < 10:
        issues.append(f"Low text-to-HTML ratio: {result.text_to_html_ratio}% (recommended 10%+)")
    if result.avg_sentence_length > 25:
        issues.append(f"Long average sentence length: {result.avg_sentence_length} words")

    if result.flesch_reading_ease < 30:
        issues.append(
            f"Very difficult readability (Flesch: {result.flesch_reading_ease}). "
            "Consider simplifying for broader audience."
        )
    elif result.flesch_reading_ease < 50:
        issues.append(
            f"Difficult readability (Flesch: {result.flesch_reading_ease}). May be hard for general audience."
        )

    # Keyword stuffing check
    for word, density in result.keyword_density.items():
        if density > 3.0:
            issues.append(f"Possible keyword stuffing: '{word}' appears at {density}% density (>3%)")

    result.issues = issues
    return result


# ── Report formatter ─────────────────────────────────────────


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

    lines.append("## Readability Scores")
    lines.append(f"- **Flesch Reading Ease**: {analysis.flesch_reading_ease}/100")
    lines.append(f"- **Flesch-Kincaid Grade**: {analysis.flesch_kincaid_grade}")
    lines.append(f"- **Level**: {analysis.readability_level}")
    lines.append("")

    if analysis.top_keywords:
        lines.append("## Top Keywords")
        for word, count in analysis.top_keywords:
            density = analysis.keyword_density.get(word, 0)
            lines.append(f"- **{word}**: {count} ({density}%)")
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
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
