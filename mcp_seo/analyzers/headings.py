"""Heading hierarchy analysis (h1-h6) with length, duplicate, and keyword checks."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from mcp_seo.utils import get_logger, parse_html

logger = get_logger("headings")


class HeadingItem(BaseModel):
    level: int
    text: str
    length: int = 0


class HeadingsAnalysis(BaseModel):
    headings: list[HeadingItem] = []
    h1_count: int = 0
    total_count: int = 0
    hierarchy_valid: bool = True
    duplicate_headings: list[str] = []
    long_headings: list[str] = []
    issues: list[str] = []


def analyze_headings(html: str) -> HeadingsAnalysis:
    """Analyze the heading hierarchy of a page."""
    soup = parse_html(html)
    result = HeadingsAnalysis()
    issues: list[str] = []

    # Collect all heading tags in document order
    all_heading_tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    headings: list[HeadingItem] = []
    for tag in all_heading_tags:
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        if text:
            headings.append(HeadingItem(level=level, text=text, length=len(text)))

    result.headings = headings
    result.total_count = len(headings)
    result.h1_count = sum(1 for h in headings if h.level == 1)

    # Validate H1
    if result.h1_count == 0:
        issues.append("CRITICAL: No <h1> tag found. Add exactly one <h1> describing the page's main topic.")
        result.hierarchy_valid = False
    elif result.h1_count > 1:
        issues.append(
            f"WARNING: Multiple H1 tags found ({result.h1_count}). "
            f"Keep only one <h1> per page describing the main topic."
        )
        result.hierarchy_valid = False

    # Check for skipped levels
    prev_level = 0
    for h in headings:
        if h.level > prev_level + 1 and prev_level > 0:
            issues.append(
                f"Heading level skipped: h{prev_level} -> h{h.level} ('{h.text[:50]}'). "
                f"Add an h{prev_level + 1} before this heading."
            )
            result.hierarchy_valid = False
        prev_level = h.level

    # Check for empty or very short headings
    for h in headings:
        if len(h.text) < 3:
            issues.append(f"Very short h{h.level}: '{h.text}'")

    # Check for long headings (>70 chars)
    for h in headings:
        if h.length > 70:
            result.long_headings.append(f"h{h.level}: '{h.text[:50]}...' ({h.length} chars)")
            issues.append(f"Long h{h.level} heading ({h.length} chars): '{h.text[:40]}...'")

    # Check for duplicate headings
    heading_texts = [h.text.lower().strip() for h in headings]
    counts = Counter(heading_texts)
    for text, count in counts.items():
        if count > 1:
            result.duplicate_headings.append(f"'{text}' appears {count} times")
            issues.append(f"Duplicate heading: '{text[:50]}' appears {count} times")

    # Too few or too many headings
    if result.total_count < 2 and result.total_count > 0:
        issues.append("Very few headings — consider adding more structure")

    result.issues = issues
    return result


def format_headings_report(analysis: HeadingsAnalysis) -> str:
    """Format headings analysis as a readable report."""
    lines = ["# Heading Hierarchy Analysis", ""]

    lines.append(f"**Total headings**: {analysis.total_count}")
    lines.append(f"**H1 count**: {analysis.h1_count}")
    lines.append(f"**Hierarchy valid**: {'Yes' if analysis.hierarchy_valid else 'No'}")
    lines.append("")

    lines.append("## Heading Structure")
    for h in analysis.headings:
        indent = "  " * (h.level - 1)
        lines.append(f"{indent}- **h{h.level}**: {h.text[:100]}")
    lines.append("")

    if analysis.duplicate_headings:
        lines.append("## Duplicate Headings")
        for dup in analysis.duplicate_headings:
            lines.append(f"- {dup}")
        lines.append("")

    if analysis.long_headings:
        lines.append("## Long Headings (>70 chars)")
        for lh in analysis.long_headings:
            lines.append(f"- {lh}")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
