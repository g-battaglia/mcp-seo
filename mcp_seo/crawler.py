"""Multi-page site crawler with cross-page SEO analysis."""

from __future__ import annotations

import asyncio
from collections import Counter
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from playwright.async_api import Page
from pydantic import BaseModel

from mcp_seo.browser import get_browser, get_page
from mcp_seo.utils import get_logger, parse_html_fresh

logger = get_logger("crawler")

# Tracking / session parameters to strip during URL normalization
_STRIP_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "twclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "affiliate",
    "sid",
    "session_id",
    "sessionid",
    "phpsessid",
    "jsessionid",
    "aspsessionid",
    "cfid",
    "cftoken",
    "_ga",
    "_gl",
}


# ── Models ────────────────────────────────────────────────────


class PageResult(BaseModel):
    url: str
    status_code: int = 200
    title: str | None = None
    description: str | None = None
    h1: str | None = None
    word_count: int = 0
    has_canonical: bool = False
    canonical_url: str | None = None
    issues: list[str] = []


class CrawlResult(BaseModel):
    base_url: str
    pages_crawled: int = 0
    pages_found: int = 0
    max_pages: int = 50
    pages: list[PageResult] = []

    # Cross-page analysis
    duplicate_titles: list[str] = []
    duplicate_descriptions: list[str] = []
    duplicate_h1s: list[str] = []
    pages_without_title: list[str] = []
    pages_without_description: list[str] = []
    pages_without_h1: list[str] = []
    orphan_pages: list[str] = []
    broken_internal_links: list[tuple[str, str, int]] = []  # (from_url, to_url, status)

    issues: list[str] = []


# ── Crawler ───────────────────────────────────────────────────


def _normalize_url(url: str) -> str:
    """Normalize a URL: strip tracking params, fragments, trailing slash."""
    parsed = urlparse(url)
    # Strip fragment
    # Strip tracking/session query parameters
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        clean_params = {k: v for k, v in params.items() if k.lower() not in _STRIP_PARAMS}
        query = urlencode(clean_params, doseq=True) if clean_params else ""
    else:
        query = ""

    path = parsed.path
    # Remove trailing slash (except root)
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


def _fetch_robots_blocked_paths(base_url: str) -> set[str]:
    """Fetch robots.txt and return set of disallowed paths for * user-agent."""
    from mcp_seo.fetcher import fetch

    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    blocked: set[str] = set()
    try:
        result = fetch(robots_url, timeout=10.0)
        if result.status_code == 200:
            current_ua = None
            for line in result.body.splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if ":" not in line:
                    continue
                directive, _, value = line.partition(":")
                directive = directive.strip().lower()
                value = value.strip()
                if directive == "user-agent":
                    current_ua = value
                elif directive == "disallow" and current_ua == "*" and value:
                    blocked.add(value)
    except Exception:
        logger.debug("Could not fetch robots.txt for %s", base_url)
    return blocked


def _is_blocked_by_robots(path: str, blocked_paths: set[str]) -> bool:
    """Check if a URL path is blocked by robots.txt disallow rules."""
    for pattern in blocked_paths:
        if pattern.endswith("*"):
            if path.startswith(pattern[:-1]):
                return True
        elif pattern.endswith("$"):
            if path == pattern[:-1]:
                return True
        elif path.startswith(pattern):
            return True
    return False


async def _crawl_page(page: Page, url: str) -> tuple[PageResult, list[str]]:
    """Crawl a single page and extract SEO data + internal links."""
    result = PageResult(url=url)
    internal_links: list[str] = []
    parsed_base = urlparse(url)
    base_domain = parsed_base.netloc

    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        if response:
            result.status_code = response.status

        html = await page.content()
        soup = parse_html_fresh(html)

        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            result.title = title_tag.string.strip()
        else:
            result.issues.append("Missing title")

        # Description
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            result.description = str(desc["content"]).strip()
        else:
            result.issues.append("Missing meta description")

        # H1
        h1_tag = soup.find("h1")
        if h1_tag:
            result.h1 = h1_tag.get_text(strip=True)
        else:
            result.issues.append("Missing H1")

        # Word count
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text = soup.get_text(separator=" ", strip=True)
        result.word_count = len(text.split())

        if result.word_count < 300:
            result.issues.append(f"Thin content ({result.word_count} words)")

        # Canonical
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            result.has_canonical = True
            result.canonical_url = str(canonical["href"])
        else:
            result.issues.append("Missing canonical")

        # Extract internal links
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"]).strip()
            if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                continue

            full_url = urljoin(url, href)
            parsed = urlparse(full_url)

            # Only follow internal links
            if parsed.netloc == base_domain:
                clean_url = _normalize_url(full_url)
                internal_links.append(clean_url)

    except Exception as e:
        result.issues.append(f"Error crawling: {e}")
        logger.warning("Error crawling %s: %s", url, e)

    return result, internal_links


async def _crawl_site(
    start_url: str,
    max_pages: int = 50,
    *,
    delay_ms: int = 500,
    respect_robots: bool = True,
) -> CrawlResult:
    """Crawl a website starting from a URL.

    Args:
        start_url: The starting URL to crawl.
        max_pages: Maximum number of pages to crawl.
        delay_ms: Delay between requests in milliseconds (rate limiting).
        respect_robots: Whether to check robots.txt before crawling.
    """
    result = CrawlResult(base_url=start_url, max_pages=max_pages)

    # Fetch robots.txt disallow rules
    blocked_paths: set[str] = set()
    if respect_robots:
        blocked_paths = _fetch_robots_blocked_paths(start_url)
        if blocked_paths:
            logger.info("Loaded %d disallow rules from robots.txt", len(blocked_paths))

    visited: set[str] = set()
    to_visit: list[str] = [_normalize_url(start_url)]
    all_internal_links: dict[str, set[str]] = {}  # url -> set of pages linking to it
    pages: list[PageResult] = []

    async with get_browser() as browser, get_page(browser) as page:
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            normalized = _normalize_url(current_url)

            if normalized in visited:
                continue

            # Check robots.txt
            if respect_robots and blocked_paths:
                url_path = urlparse(normalized).path
                if _is_blocked_by_robots(url_path, blocked_paths):
                    logger.info("Skipping (blocked by robots.txt): %s", normalized)
                    continue

            visited.add(normalized)
            logger.info("Crawling [%d/%d]: %s", len(visited), max_pages, normalized)

            page_result, found_links = await _crawl_page(page, normalized)
            pages.append(page_result)

            # Track internal links (for orphan detection)
            for link in found_links:
                link = _normalize_url(link)
                if link not in all_internal_links:
                    all_internal_links[link] = set()
                all_internal_links[link].add(normalized)

                if link not in visited:
                    to_visit.append(link)

            # Rate limiting
            if delay_ms > 0 and to_visit:
                await asyncio.sleep(delay_ms / 1000.0)

    result.pages = pages
    result.pages_crawled = len(pages)
    result.pages_found = len(all_internal_links) + 1  # +1 for start URL

    # ── Cross-page analysis ──────────────────────────────────

    # Duplicate titles
    titles = [(p.url, p.title) for p in pages if p.title]
    title_counter = Counter(t for _, t in titles)
    for title, count in title_counter.items():
        if count > 1:
            urls = [url for url, t in titles if t == title]
            result.duplicate_titles.append(f"'{title}' on {count} pages: {', '.join(urls[:3])}")

    # Duplicate descriptions
    descs = [(p.url, p.description) for p in pages if p.description]
    desc_counter = Counter(d for _, d in descs)
    for desc, count in desc_counter.items():
        if count > 1:
            urls = [url for url, d in descs if d == desc]
            result.duplicate_descriptions.append(f"'{desc[:60]}...' on {count} pages: {', '.join(urls[:3])}")

    # Duplicate H1s
    h1s = [(p.url, p.h1) for p in pages if p.h1]
    h1_counter = Counter(h for _, h in h1s)
    for h1, count in h1_counter.items():
        if count > 1:
            urls = [url for url, h in h1s if h == h1]
            result.duplicate_h1s.append(f"'{h1}' on {count} pages: {', '.join(urls[:3])}")

    # Missing elements
    result.pages_without_title = [p.url for p in pages if not p.title]
    result.pages_without_description = [p.url for p in pages if not p.description]
    result.pages_without_h1 = [p.url for p in pages if not p.h1]

    # Orphan pages (pages not linked from any other page, except start)
    for page_result in pages:
        if page_result.url != start_url and page_result.url not in all_internal_links:
            result.orphan_pages.append(page_result.url)

    # Summary issues
    issues: list[str] = []
    if result.duplicate_titles:
        issues.append(f"{len(result.duplicate_titles)} duplicate title(s) found")
    if result.duplicate_descriptions:
        issues.append(f"{len(result.duplicate_descriptions)} duplicate description(s) found")
    if result.duplicate_h1s:
        issues.append(f"{len(result.duplicate_h1s)} duplicate H1(s) found")
    if result.pages_without_title:
        issues.append(f"{len(result.pages_without_title)} page(s) without title")
    if result.pages_without_description:
        issues.append(f"{len(result.pages_without_description)} page(s) without meta description")
    if result.pages_without_h1:
        issues.append(f"{len(result.pages_without_h1)} page(s) without H1")
    if result.orphan_pages:
        issues.append(f"{len(result.orphan_pages)} orphan page(s) (not linked from other pages)")

    result.issues = issues
    return result


def crawl_site(start_url: str, max_pages: int = 50) -> CrawlResult:
    """Crawl a website (sync wrapper)."""
    return asyncio.run(_crawl_site(start_url, max_pages=max_pages))


# ── Report formatter ──────────────────────────────────────────


def format_crawl_report(result: CrawlResult) -> str:
    """Format crawl results as a readable report."""
    lines = ["# Site Crawl Report", ""]

    lines.append(f"**Base URL**: {result.base_url}")
    lines.append(f"**Pages Crawled**: {result.pages_crawled}")
    lines.append(f"**Pages Discovered**: {result.pages_found}")
    lines.append(f"**Max Pages**: {result.max_pages}")
    lines.append("")

    # Page summary table
    lines.append("## Pages Crawled")
    lines.append("")
    lines.append("| URL | Title | H1 | Words | Issues |")
    lines.append("|-----|-------|----|----|--------|")
    for p in result.pages:
        title = (p.title or "MISSING")[:40]
        h1 = (p.h1 or "MISSING")[:30]
        issue_count = len(p.issues)
        lines.append(f"| {p.url[:60]} | {title} | {h1} | {p.word_count} | {issue_count} |")
    lines.append("")

    # Cross-page issues
    if result.duplicate_titles:
        lines.append("## Duplicate Titles")
        for dup in result.duplicate_titles:
            lines.append(f"- {dup}")
        lines.append("")

    if result.duplicate_descriptions:
        lines.append("## Duplicate Descriptions")
        for dup in result.duplicate_descriptions:
            lines.append(f"- {dup}")
        lines.append("")

    if result.duplicate_h1s:
        lines.append("## Duplicate H1 Tags")
        for dup in result.duplicate_h1s:
            lines.append(f"- {dup}")
        lines.append("")

    if result.pages_without_title:
        lines.append("## Pages Without Title")
        for url in result.pages_without_title:
            lines.append(f"- {url}")
        lines.append("")

    if result.pages_without_description:
        lines.append("## Pages Without Meta Description")
        for url in result.pages_without_description:
            lines.append(f"- {url}")
        lines.append("")

    if result.orphan_pages:
        lines.append("## Orphan Pages (not linked internally)")
        for url in result.orphan_pages:
            lines.append(f"- {url}")
        lines.append("")

    # Per-page issues
    pages_with_issues = [p for p in result.pages if p.issues]
    if pages_with_issues:
        lines.append("## Per-Page Issues")
        for p in pages_with_issues:
            lines.append(f"\n### {p.url}")
            for issue in p.issues:
                lines.append(f"- {issue}")
        lines.append("")

    # Summary
    if result.issues:
        lines.append("## Summary")
        for issue in result.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
