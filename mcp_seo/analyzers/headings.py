"""Heading hierarchy analysis (h1-h6)."""

from __future__ import annotations

from bs4 import BeautifulSoup
from pydantic import BaseModel


class HeadingItem(BaseModel):
    level: int
    text: str


class HeadingsAnalysis(BaseModel):
    headings: list[HeadingItem] = []
    h1_count: int = 0
    total_count: int = 0
    hierarchy_valid: bool = True
    issues: list[str] = []


def analyze_headings(html: str) -> HeadingsAnalysis:
    """Analyze the heading hierarchy of a page."""
    soup = BeautifulSoup(html, "lxml")
    result = HeadingsAnalysis()
    issues: list[str] = []

    headings: list[HeadingItem] = []
    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            text = tag.get_text(strip=True)
            if text:
                headings.append(HeadingItem(level=level, text=text))

    # Re-sort by document order
    all_heading_tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    headings = []
    for tag in all_heading_tags:
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        if text:
            headings.append(HeadingItem(level=level, text=text))

    result.headings = headings
    result.total_count = len(headings)
    result.h1_count = sum(1 for h in headings if h.level == 1)

    # Validate
    if result.h1_count == 0:
        issues.append("No <h1> tag found")
        result.hierarchy_valid = False
    elif result.h1_count > 1:
        issues.append(f"Multiple <h1> tags found ({result.h1_count})")
        result.hierarchy_valid = False

    # Check for skipped levels
    prev_level = 0
    for h in headings:
        if h.level > prev_level + 1 and prev_level > 0:
            issues.append(f"Heading level skipped: h{prev_level} → h{h.level} ('{h.text[:50]}')")
            result.hierarchy_valid = False
        prev_level = h.level

    # Check for empty or very short headings
    for h in headings:
        if len(h.text) < 3:
            issues.append(f"Very short h{h.level}: '{h.text}'")

    result.issues = issues
    return result


def format_headings_report(analysis: HeadingsAnalysis) -> str:
    """Format headings analysis as a readable report."""
    lines = ["# Heading Hierarchy Analysis", ""]

    lines.append(f"**Total headings**: {analysis.total_count}")
    lines.append(f"**H1 count**: {analysis.h1_count}")
    lines.append(f"**Hierarchy valid**: {'✅ Yes' if analysis.hierarchy_valid else '❌ No'}")
    lines.append("")

    lines.append("## Heading Structure")
    for h in analysis.headings:
        indent = "  " * (h.level - 1)
        lines.append(f"{indent}- **h{h.level}**: {h.text}")
    lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
