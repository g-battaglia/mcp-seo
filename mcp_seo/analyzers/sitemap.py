"""Sitemap discovery and analysis."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from pydantic import BaseModel

from mcp_seo.fetcher import fetch


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
                lastmod=lastmod.text.strip()
                if lastmod is not None and lastmod.text
                else None,
                changefreq=changefreq.text.strip()
                if changefreq is not None and changefreq.text
                else None,
                priority=priority.text.strip()
                if priority is not None and priority.text
                else None,
            )
        )

    return urls, sub_sitemaps


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
                "<?xml" in resp.body[:100]
                or "<urlset" in resp.body[:200]
                or "<sitemapindex" in resp.body[:200]
            ):
                result.sitemap_url = candidate
                result.found = True
                urls, sub_sitemaps = _parse_sitemap_xml(resp.body)
                result.urls = urls
                result.sub_sitemaps = sub_sitemaps
                result.url_count = len(urls)

                # Recursively fetch sub-sitemaps (up to 5)
                for sub_url in sub_sitemaps[:5]:
                    try:
                        sub_resp = fetch(sub_url)
                        if sub_resp.status_code == 200:
                            sub_urls, _ = _parse_sitemap_xml(sub_resp.body)
                            result.urls.extend(sub_urls)
                            result.url_count += len(sub_urls)
                    except Exception:
                        issues.append(f"Failed to fetch sub-sitemap: {sub_url}")

                break
        except Exception:
            continue

    if not result.found:
        issues.append("No sitemap.xml found")

    if result.url_count == 0 and result.found:
        issues.append("Sitemap found but contains no URLs")

    # Check for common issues
    urls_without_lastmod = sum(1 for u in result.urls if not u.lastmod)
    if urls_without_lastmod > 0 and result.urls:
        issues.append(
            f"{urls_without_lastmod}/{len(result.urls)} URLs missing lastmod dates"
        )

    result.issues = issues
    return result


def format_sitemap_report(analysis: SitemapAnalysis) -> str:
    """Format sitemap analysis as a readable report."""
    lines = ["# Sitemap Analysis", ""]

    lines.append(f"**Sitemap URL**: {analysis.sitemap_url or '❌ Not found'}")
    lines.append(f"**Found**: {'✅ Yes' if analysis.found else '❌ No'}")
    lines.append(f"**Total URLs**: {analysis.url_count}")
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
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
