"""Link analysis: internal, external, broken, rel types, pagination."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel

from mcp_seo.fetcher import check_url
from mcp_seo.utils import get_logger, parse_html

logger = get_logger("links")


class LinkItem(BaseModel):
    href: str
    text: str
    is_internal: bool
    is_nofollow: bool
    is_sponsored: bool = False
    is_ugc: bool = False
    status_code: int = 0
    is_broken: bool = False


class LinksAnalysis(BaseModel):
    total_links: int = 0
    internal_links: list[LinkItem] = []
    external_links: list[LinkItem] = []
    broken_links: list[LinkItem] = []
    nofollow_links: list[LinkItem] = []
    sponsored_links: list[LinkItem] = []
    ugc_links: list[LinkItem] = []
    links_without_text: list[LinkItem] = []

    # Pagination
    has_pagination: bool = False
    prev_page: str | None = None
    next_page: str | None = None

    # Ratios
    follow_ratio: float = 0.0
    internal_ratio: float = 0.0

    issues: list[str] = []


def analyze_links(html: str, base_url: str, *, check_broken: bool = False) -> LinksAnalysis:
    """Analyze all links on a page."""
    soup = parse_html(html)
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    # Check for <base> tag that overrides URL resolution
    base_tag = soup.find("base", href=True)
    resolve_base = str(base_tag["href"]) if base_tag else base_url

    result = LinksAnalysis()
    all_links: list[LinkItem] = []

    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag["href"]).strip()
        text = a_tag.get_text(strip=True)
        rel = a_tag.get("rel", [])
        if isinstance(rel, str):
            rel = rel.split()
        rel_set = set(str(r).lower() for r in rel) if rel else set()

        is_nofollow = "nofollow" in rel_set
        is_sponsored = "sponsored" in rel_set
        is_ugc = "ugc" in rel_set

        # Skip anchors, javascript, mailto, tel, data
        if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue

        # Resolve relative URLs using <base> tag if present
        full_url = urljoin(resolve_base, href)
        parsed = urlparse(full_url)

        is_internal = parsed.netloc == base_domain or not parsed.netloc

        link = LinkItem(
            href=full_url,
            text=text,
            is_internal=is_internal,
            is_nofollow=is_nofollow,
            is_sponsored=is_sponsored,
            is_ugc=is_ugc,
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
        if is_sponsored:
            result.sponsored_links.append(link)
        if is_ugc:
            result.ugc_links.append(link)

        if is_internal:
            result.internal_links.append(link)
        else:
            result.external_links.append(link)

        all_links.append(link)

    result.total_links = len(all_links)

    # Pagination detection
    prev_link = soup.find("link", attrs={"rel": "prev"})
    next_link = soup.find("link", attrs={"rel": "next"})
    if prev_link and prev_link.get("href"):
        result.has_pagination = True
        result.prev_page = str(prev_link["href"])
    if next_link and next_link.get("href"):
        result.has_pagination = True
        result.next_page = str(next_link["href"])

    # Calculate ratios
    if result.total_links > 0:
        follow_count = result.total_links - len(result.nofollow_links)
        result.follow_ratio = round(follow_count / result.total_links * 100, 1)
        result.internal_ratio = round(len(result.internal_links) / result.total_links * 100, 1)

    # Check for broken links if requested (parallel for speed)
    if check_broken:
        from mcp_seo.config import Config

        logger.info("Checking %d links for broken URLs...", len(all_links))

        def _check_link(link: LinkItem) -> LinkItem:
            status, _ = check_url(link.href)
            link.status_code = status
            if status == 0 or status >= 400:
                link.is_broken = True
            return link

        with ThreadPoolExecutor(max_workers=Config.link_check_workers()) as executor:
            futures = {executor.submit(_check_link, link): link for link in all_links}
            for future in as_completed(futures):
                link = future.result()
                if link.is_broken:
                    result.broken_links.append(link)

    # Issues
    issues: list[str] = []
    if not result.internal_links:
        issues.append("No internal links found")
    if result.links_without_text:
        issues.append(f"{len(result.links_without_text)} links without anchor text")
    if result.broken_links:
        issues.append(f"{len(result.broken_links)} broken links found")
    if result.total_links > 0 and result.follow_ratio < 50:
        issues.append(f"Low follow ratio: {result.follow_ratio}% of links are followed")

    result.issues = issues
    return result


def format_links_report(analysis: LinksAnalysis) -> str:
    """Format links analysis as a readable report."""
    lines = ["# Link Analysis", ""]

    lines.append(f"**Total links**: {analysis.total_links}")
    lines.append(f"**Internal**: {len(analysis.internal_links)} ({analysis.internal_ratio}%)")
    lines.append(f"**External**: {len(analysis.external_links)}")
    lines.append(f"**Nofollow**: {len(analysis.nofollow_links)}")
    lines.append(f"**Sponsored**: {len(analysis.sponsored_links)}")
    lines.append(f"**UGC**: {len(analysis.ugc_links)}")
    lines.append(f"**Follow ratio**: {analysis.follow_ratio}%")
    lines.append(f"**Broken**: {len(analysis.broken_links)}")
    lines.append("")

    if analysis.has_pagination:
        lines.append("## Pagination")
        if analysis.prev_page:
            lines.append(f"- **Prev**: {analysis.prev_page}")
        if analysis.next_page:
            lines.append(f"- **Next**: {analysis.next_page}")
        lines.append("")

    if analysis.internal_links:
        lines.append("## Internal Links (first 30)")
        for link in analysis.internal_links[:30]:
            status = f" [{link.status_code}]" if link.status_code else ""
            lines.append(f"- [{link.text or 'NO TEXT'}]({link.href}){status}")
        if len(analysis.internal_links) > 30:
            lines.append(f"- ... and {len(analysis.internal_links) - 30} more")
        lines.append("")

    if analysis.external_links:
        lines.append("## External Links (first 30)")
        for link in analysis.external_links[:30]:
            status = f" [{link.status_code}]" if link.status_code else ""
            attrs = []
            if link.is_nofollow:
                attrs.append("nofollow")
            if link.is_sponsored:
                attrs.append("sponsored")
            if link.is_ugc:
                attrs.append("ugc")
            attr_str = f" [{', '.join(attrs)}]" if attrs else ""
            lines.append(f"- [{link.text or 'NO TEXT'}]({link.href}){status}{attr_str}")
        if len(analysis.external_links) > 30:
            lines.append(f"- ... and {len(analysis.external_links) - 30} more")
        lines.append("")

    if analysis.broken_links:
        lines.append("## Broken Links")
        for link in analysis.broken_links:
            lines.append(f"- [{link.text}]({link.href}) -> HTTP {link.status_code}")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
