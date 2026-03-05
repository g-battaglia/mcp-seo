"""Sitemap discovery and analysis with URL count limits, gzip support, lastmod validation."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse

from defusedxml import ElementTree
from pydantic import BaseModel

from mcp_seo.config import Config
from mcp_seo.fetcher import fetch
from mcp_seo.utils import get_logger

logger = get_logger("sitemap")

# Google limits
MAX_URLS_PER_SITEMAP = 50_000
MAX_SITEMAP_SIZE_BYTES = 50 * 1024 * 1024  # 50MB uncompressed

MAX_SUB_SITEMAPS_TO_FETCH = Config.max_sub_sitemaps()


class SitemapUrl(BaseModel):
    loc: str
    lastmod: str | None = None
    changefreq: str | None = None
    priority: str | None = None


class SitemapAnalysis(BaseModel):
    sitemap_url: str | None = None
    found: bool = False
    url_count: int = 0
    urls: list[SitemapUrl] = []
    sub_sitemaps: list[str] = []

    # New fields
    is_index: bool = False
    total_sub_sitemaps: int = 0
    size_bytes: int = 0
    urls_over_limit: bool = False
    lastmod_format_valid: bool = True
    stale_lastmod_count: int = 0

    issues: list[str] = []


def _parse_sitemap_xml(xml_text: str) -> tuple[list[SitemapUrl], list[str]]:
    """Parse sitemap XML and return URLs and sub-sitemaps."""
    urls: list[SitemapUrl] = []
    sub_sitemaps: list[str] = []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return urls, sub_sitemaps

    # Handle namespace
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    # Check for sitemap index
    for sitemap in root.findall(f"{ns}sitemap"):
        loc = sitemap.find(f"{ns}loc")
        if loc is not None and loc.text:
            sub_sitemaps.append(loc.text.strip())

    # Check for URL entries
    for url_elem in root.findall(f"{ns}url"):
        loc = url_elem.find(f"{ns}loc")
        if loc is None or not loc.text:
            continue

        lastmod = url_elem.find(f"{ns}lastmod")
        changefreq = url_elem.find(f"{ns}changefreq")
        priority = url_elem.find(f"{ns}priority")

        urls.append(
            SitemapUrl(
                loc=loc.text.strip(),
                lastmod=lastmod.text.strip() if lastmod is not None and lastmod.text else None,
                changefreq=changefreq.text.strip() if changefreq is not None and changefreq.text else None,
                priority=priority.text.strip() if priority is not None and priority.text else None,
            )
        )

    return urls, sub_sitemaps


def _validate_lastmod(lastmod: str) -> bool:
    """Validate lastmod is in W3C Datetime format."""
    patterns = [
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # Full datetime
        r"^\d{4}-\d{2}-\d{2}$",  # Date only
        r"^\d{4}-\d{2}$",  # Year-month
        r"^\d{4}$",  # Year only
    ]
    return any(re.match(p, lastmod) for p in patterns)


def _is_stale(lastmod: str, months: int = 12) -> bool:
    """Check if lastmod is older than N months."""
    try:
        dt: datetime | None = None
        # Strip timezone suffix for naive parsing (we only care about staleness)
        clean = lastmod.strip()
        # Remove timezone info (+00:00, Z, etc.) for consistent parsing
        clean = re.sub(r"[Zz]$", "", clean)
        clean = re.sub(r"[+-]\d{2}:\d{2}$", "", clean)

        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                dt = datetime.strptime(clean, fmt)
                break
            except ValueError:
                continue

        if dt is None:
            # Last resort: try just the first 10 chars as date
            try:
                dt = datetime.strptime(clean[:10], "%Y-%m-%d")
            except ValueError:
                return False

        days_old = (datetime.now() - dt).days
        return days_old > months * 30
    except Exception:
        return False


def analyze_sitemap(base_url: str) -> SitemapAnalysis:
    """Discover and analyze sitemaps for a domain."""
    result = SitemapAnalysis()
    issues: list[str] = []
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Try common sitemap locations
    sitemap_candidates = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap/sitemap.xml",
    ]

    # Also check robots.txt for sitemap directives
    try:
        robots_result = fetch(f"{base}/robots.txt")
        if robots_result.status_code == 200:
            for line in robots_result.body.splitlines():
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url not in sitemap_candidates:
                        sitemap_candidates.insert(0, sitemap_url)
    except Exception:
        pass

    for candidate in sitemap_candidates:
        try:
            resp = fetch(candidate)
            if resp.status_code == 200 and (
                "<?xml" in resp.body[:100] or "<urlset" in resp.body[:200] or "<sitemapindex" in resp.body[:200]
            ):
                result.sitemap_url = candidate
                result.found = True
                result.size_bytes = len(resp.body.encode("utf-8"))

                # Check size limit
                if result.size_bytes > MAX_SITEMAP_SIZE_BYTES:
                    issues.append(f"Sitemap exceeds 50MB limit ({result.size_bytes / 1024 / 1024:.1f}MB)")

                urls, sub_sitemaps = _parse_sitemap_xml(resp.body)
                result.urls = urls
                result.sub_sitemaps = sub_sitemaps
                result.url_count = len(urls)
                result.is_index = bool(sub_sitemaps)
                result.total_sub_sitemaps = len(sub_sitemaps)

                # URL count limit
                if result.url_count > MAX_URLS_PER_SITEMAP:
                    result.urls_over_limit = True
                    issues.append(f"Sitemap exceeds 50,000 URL limit ({result.url_count} URLs)")

                # Recursively fetch sub-sitemaps
                for sub_url in sub_sitemaps[:MAX_SUB_SITEMAPS_TO_FETCH]:
                    try:
                        sub_resp = fetch(sub_url)
                        if sub_resp.status_code == 200:
                            sub_urls, _ = _parse_sitemap_xml(sub_resp.body)
                            result.urls.extend(sub_urls)
                            result.url_count += len(sub_urls)
                    except Exception as e:
                        logger.warning("Failed to fetch sub-sitemap %s: %s", sub_url, e)
                        issues.append(f"Failed to fetch sub-sitemap: {sub_url}")

                if len(sub_sitemaps) > MAX_SUB_SITEMAPS_TO_FETCH:
                    issues.append(f"Only fetched {MAX_SUB_SITEMAPS_TO_FETCH} of {len(sub_sitemaps)} sub-sitemaps")

                break
        except Exception:
            continue

    if not result.found:
        issues.append("No sitemap.xml found")

    if result.url_count == 0 and result.found:
        issues.append("Sitemap found but contains no URLs")

    # Validate lastmod dates
    if result.urls:
        urls_without_lastmod = sum(1 for u in result.urls if not u.lastmod)
        if urls_without_lastmod > 0:
            issues.append(f"{urls_without_lastmod}/{len(result.urls)} URLs missing lastmod dates")

        # Check lastmod format
        invalid_formats = 0
        stale_count = 0
        for u in result.urls:
            if u.lastmod:
                if not _validate_lastmod(u.lastmod):
                    invalid_formats += 1
                if _is_stale(u.lastmod, months=12):
                    stale_count += 1

        if invalid_formats > 0:
            result.lastmod_format_valid = False
            issues.append(f"{invalid_formats} URLs have invalid lastmod format (should be W3C Datetime)")

        result.stale_lastmod_count = stale_count
        if stale_count > len(result.urls) * 0.5:
            issues.append(
                f"{stale_count}/{len(result.urls)} URLs have lastmod older than 12 months — "
                "consider updating or removing stale entries"
            )

    result.issues = issues
    return result


def format_sitemap_report(analysis: SitemapAnalysis) -> str:
    """Format sitemap analysis as a readable report."""
    lines = ["# Sitemap Analysis", ""]

    lines.append(f"**Sitemap URL**: {analysis.sitemap_url or 'Not found'}")
    lines.append(f"**Found**: {'Yes' if analysis.found else 'No'}")
    lines.append(f"**Total URLs**: {analysis.url_count}")
    if analysis.is_index:
        lines.append(f"**Type**: Sitemap Index ({analysis.total_sub_sitemaps} sub-sitemaps)")
    if analysis.size_bytes > 0:
        lines.append(f"**Size**: {analysis.size_bytes / 1024:.1f}KB")
    lines.append("")

    if analysis.sub_sitemaps:
        lines.append("## Sub-Sitemaps")
        for s in analysis.sub_sitemaps:
            lines.append(f"- {s}")
        lines.append("")

    if analysis.urls:
        lines.append("## URLs (first 30)")
        for url in analysis.urls[:30]:
            lastmod = f" | {url.lastmod}" if url.lastmod else ""
            priority = f" | p={url.priority}" if url.priority else ""
            lines.append(f"- {url.loc}{lastmod}{priority}")
        if len(analysis.urls) > 30:
            lines.append(f"- ... and {len(analysis.urls) - 30} more")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
