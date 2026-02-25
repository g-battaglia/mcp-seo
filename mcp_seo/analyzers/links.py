"""Link analysis: internal, external, broken links."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel

from mcp_seo.fetcher import check_url


class LinkItem(BaseModel):
    href: str
    text: str
    is_internal: bool
    is_nofollow: bool
    status_code: int = 0
    is_broken: bool = False


class LinksAnalysis(BaseModel):
    total_links: int = 0
    internal_links: list[LinkItem] = []
    external_links: list[LinkItem] = []
    broken_links: list[LinkItem] = []
    nofollow_links: list[LinkItem] = []
    links_without_text: list[LinkItem] = []
    issues: list[str] = []


def analyze_links(
    html: str, base_url: str, *, check_broken: bool = False
) -> LinksAnalysis:
    """Analyze all links on a page."""
    soup = BeautifulSoup(html, "lxml")
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    result = LinksAnalysis()
    all_links: list[LinkItem] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        text = a_tag.get_text(strip=True)
        rel = a_tag.get("rel", [])
        is_nofollow = "nofollow" in rel

        # Skip anchors, javascript, mailto, tel
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Resolve relative URLs
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        is_internal = parsed.netloc == base_domain or not parsed.netloc

        link = LinkItem(
            href=full_url,
            text=text,
            is_internal=is_internal,
            is_nofollow=is_nofollow,
        )

        if not text:
            # Check if there's an image with alt text
            img = a_tag.find("img")
            if img and img.get("alt"):
                link.text = f"[img: {img['alt']}]"
            else:
                result.links_without_text.append(link)

        if is_nofollow:
            result.nofollow_links.append(link)

        if is_internal:
            result.internal_links.append(link)
        else:
            result.external_links.append(link)

        all_links.append(link)

    result.total_links = len(all_links)

    # Check for broken links if requested
    if check_broken:
        for link in all_links:
            status, _ = check_url(link.href)
            link.status_code = status
            if status == 0 or status >= 400:
                link.is_broken = True
                result.broken_links.append(link)

    # Issues
    issues: list[str] = []
    if not result.internal_links:
        issues.append("No internal links found")
    if result.links_without_text:
        issues.append(f"{len(result.links_without_text)} links without anchor text")
    if result.broken_links:
        issues.append(f"{len(result.broken_links)} broken links found")

    result.issues = issues
    return result


def format_links_report(analysis: LinksAnalysis) -> str:
    """Format links analysis as a readable report."""
    lines = ["# Link Analysis", ""]

    lines.append(f"**Total links**: {analysis.total_links}")
    lines.append(f"**Internal**: {len(analysis.internal_links)}")
    lines.append(f"**External**: {len(analysis.external_links)}")
    lines.append(f"**Nofollow**: {len(analysis.nofollow_links)}")
    lines.append(f"**Broken**: {len(analysis.broken_links)}")
    lines.append("")

    if analysis.internal_links:
        lines.append("## Internal Links (first 20)")
        for link in analysis.internal_links[:20]:
            status = f" [{link.status_code}]" if link.status_code else ""
            lines.append(f"- [{link.text or 'NO TEXT'}]({link.href}){status}")
        if len(analysis.internal_links) > 20:
            lines.append(f"- ... and {len(analysis.internal_links) - 20} more")
        lines.append("")

    if analysis.external_links:
        lines.append("## External Links (first 20)")
        for link in analysis.external_links[:20]:
            status = f" [{link.status_code}]" if link.status_code else ""
            nofollow = " [nofollow]" if link.is_nofollow else ""
            lines.append(f"- [{link.text or 'NO TEXT'}]({link.href}){status}{nofollow}")
        if len(analysis.external_links) > 20:
            lines.append(f"- ... and {len(analysis.external_links) - 20} more")
        lines.append("")

    if analysis.broken_links:
        lines.append("## ❌ Broken Links")
        for link in analysis.broken_links:
            lines.append(f"- [{link.text}]({link.href}) → HTTP {link.status_code}")
        lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
