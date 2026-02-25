"""Meta tags analysis: title, description, OG, Twitter Cards, canonical, etc."""

from __future__ import annotations

import json
from bs4 import BeautifulSoup
from pydantic import BaseModel


class MetaAnalysis(BaseModel):
    """Result of meta tags analysis."""

    title: str | None = None
    title_length: int = 0
    description: str | None = None
    description_length: int = 0
    canonical: str | None = None
    robots: str | None = None
    viewport: str | None = None
    charset: str | None = None
    language: str | None = None
    og_tags: dict[str, str] = {}
    twitter_tags: dict[str, str] = {}
    other_meta: dict[str, str] = {}
    issues: list[str] = []


def analyze_meta(html: str, url: str = "") -> MetaAnalysis:
    """Analyze meta tags from HTML content."""
    soup = BeautifulSoup(html, "lxml")
    result = MetaAnalysis()
    issues: list[str] = []

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        result.title = title_tag.string.strip()
        result.title_length = len(result.title)
        if result.title_length < 30:
            issues.append(f"Title too short ({result.title_length} chars, recommended 30-60)")
        elif result.title_length > 60:
            issues.append(f"Title too long ({result.title_length} chars, recommended 30-60)")
    else:
        issues.append("Missing <title> tag")

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        result.description = desc["content"].strip()
        result.description_length = len(result.description)
        if result.description_length < 70:
            issues.append(f"Meta description too short ({result.description_length} chars, recommended 70-160)")
        elif result.description_length > 160:
            issues.append(f"Meta description too long ({result.description_length} chars, recommended 70-160)")
    else:
        issues.append("Missing meta description")

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        result.canonical = canonical["href"]
    else:
        issues.append("Missing canonical URL")

    # Robots
    robots = soup.find("meta", attrs={"name": "robots"})
    if robots and robots.get("content"):
        result.robots = robots["content"]
        if "noindex" in result.robots.lower():
            issues.append("Page is set to noindex")

    # Viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport and viewport.get("content"):
        result.viewport = viewport["content"]
    else:
        issues.append("Missing viewport meta tag (mobile-friendliness issue)")

    # Charset
    charset = soup.find("meta", attrs={"charset": True})
    if charset:
        result.charset = charset.get("charset", "")
    else:
        charset_http = soup.find("meta", attrs={"http-equiv": "Content-Type"})
        if charset_http:
            result.charset = charset_http.get("content", "")
        else:
            issues.append("Missing charset declaration")

    # Language
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        result.language = html_tag["lang"]
    else:
        issues.append("Missing lang attribute on <html> tag")

    # Open Graph tags
    for tag in soup.find_all("meta", attrs={"property": True}):
        prop = tag.get("property", "")
        content = tag.get("content", "")
        if prop.startswith("og:"):
            result.og_tags[prop] = content

    if not result.og_tags:
        issues.append("No Open Graph tags found")
    else:
        for required in ["og:title", "og:description", "og:image", "og:url"]:
            if required not in result.og_tags:
                issues.append(f"Missing {required} tag")

    # Twitter Card tags
    for tag in soup.find_all("meta", attrs={"name": True}):
        name = tag.get("name", "")
        content = tag.get("content", "")
        if name.startswith("twitter:"):
            result.twitter_tags[name] = content

    if not result.twitter_tags:
        issues.append("No Twitter Card tags found")

    # Other meta tags
    for tag in soup.find_all("meta"):
        name = tag.get("name", "")
        content = tag.get("content", "")
        prop = tag.get("property", "")
        if name and not name.startswith(("twitter:", "viewport", "description", "robots")):
            if not prop.startswith("og:"):
                result.other_meta[name] = content

    result.issues = issues
    return result


def format_meta_report(analysis: MetaAnalysis) -> str:
    """Format meta analysis as a readable report."""
    lines = ["# Meta Tags Analysis", ""]

    lines.append("## Basic Meta Tags")
    lines.append(f"- **Title**: {analysis.title or '❌ MISSING'}")
    lines.append(f"  - Length: {analysis.title_length} chars")
    lines.append(f"- **Description**: {analysis.description or '❌ MISSING'}")
    lines.append(f"  - Length: {analysis.description_length} chars")
    lines.append(f"- **Canonical**: {analysis.canonical or '❌ MISSING'}")
    lines.append(f"- **Robots**: {analysis.robots or 'Not set (default: index, follow)'}")
    lines.append(f"- **Viewport**: {analysis.viewport or '❌ MISSING'}")
    lines.append(f"- **Charset**: {analysis.charset or '❌ MISSING'}")
    lines.append(f"- **Language**: {analysis.language or '❌ MISSING'}")
    lines.append("")

    if analysis.og_tags:
        lines.append("## Open Graph Tags")
        for k, v in analysis.og_tags.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if analysis.twitter_tags:
        lines.append("## Twitter Card Tags")
        for k, v in analysis.twitter_tags.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
