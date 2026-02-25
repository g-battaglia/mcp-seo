"""MCP-SEO Server — exposes all SEO tools as MCP tools."""

from __future__ import annotations

import json
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mcp_seo.fetcher import fetch
from mcp_seo.browser import render_page_sync, take_screenshot_sync


mcp = FastMCP(
    "MCP-SEO",
    instructions=(
        "MCP-SEO is an open-source SEO analysis toolkit for AI agents. "
        "Use these tools to audit any webpage for on-page SEO, "
        "technical SEO, performance, mobile-friendliness, and more. "
        "All tools accept a URL and return Markdown-formatted reports."
    ),
)


# ── Helpers ───────────────────────────────────────────────────


def _ensure_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _get_html(url: str, *, rendered: bool = True) -> tuple[str, str]:
    url = _ensure_url(url)
    if rendered:
        html = render_page_sync(url)
        return html, url
    else:
        result = fetch(url)
        return result.body, result.final_url


# ── Tools: Page Fetching ─────────────────────────────────────


@mcp.tool()
def crawl(url: str) -> str:
    """Render a page with headless Chromium and return the full rendered HTML.
    Use this when the page is a SPA or uses client-side rendering."""
    url = _ensure_url(url)
    return render_page_sync(url)


@mcp.tool()
def fetch_page(url: str) -> str:
    """Fetch the raw HTTP response without JS rendering.
    Returns JSON with status code, headers, body, redirect chain, and timing."""
    url = _ensure_url(url)
    result = fetch(url)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


# ── Tools: On-Page SEO ───────────────────────────────────────


@mcp.tool()
def analyze_meta_tags(url: str) -> str:
    """Analyze meta tags: title, meta description, canonical, robots,
    viewport, charset, lang, Open Graph tags, and Twitter Card tags."""
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report

    html, final_url = _get_html(url)
    return format_meta_report(analyze_meta(html, final_url))


@mcp.tool()
def analyze_headings(url: str) -> str:
    """Extract and validate the heading hierarchy (h1-h6).
    Checks for single H1, skipped levels, and empty headings."""
    from mcp_seo.analyzers.headings import (
        analyze_headings as _analyze,
        format_headings_report,
    )

    html, _ = _get_html(url)
    return format_headings_report(_analyze(html))


@mcp.tool()
def analyze_links(url: str) -> str:
    """Analyze all links on a page: internal vs external count,
    nofollow detection, anchor text analysis, and links without text."""
    from mcp_seo.analyzers.links import (
        analyze_links as _analyze,
        format_links_report,
    )

    html, final_url = _get_html(url)
    return format_links_report(_analyze(html, final_url))


@mcp.tool()
def analyze_images(url: str) -> str:
    """Audit images: alt text presence, lazy loading, explicit
    dimensions (width/height for CLS), and modern format usage (WebP/AVIF)."""
    from mcp_seo.analyzers.images import (
        analyze_images as _analyze,
        format_images_report,
    )

    html, final_url = _get_html(url)
    return format_images_report(_analyze(html, final_url))


@mcp.tool()
def analyze_content(url: str) -> str:
    """Analyze page content: word count, character count, sentence count,
    paragraph count, average sentence length, reading time, text-to-HTML
    ratio, top keywords, bigrams, and trigrams."""
    from mcp_seo.analyzers.content import (
        analyze_content as _analyze,
        format_content_report,
    )

    html, _ = _get_html(url)
    return format_content_report(_analyze(html))


# ── Tools: Technical SEO ─────────────────────────────────────


@mcp.tool()
def analyze_headers(url: str) -> str:
    """Inspect HTTP response headers: caching (Cache-Control, ETag),
    security (HSTS, CSP, X-Frame-Options), compression, server info, redirect chain."""
    from mcp_seo.analyzers.headers import (
        analyze_headers as _analyze,
        format_headers_report,
    )

    url = _ensure_url(url)
    result = fetch(url)
    return format_headers_report(
        _analyze(result.headers, result.status_code, result.redirect_chain)
    )


@mcp.tool()
def analyze_sitemap(url: str) -> str:
    """Discover and parse XML sitemaps: checks /sitemap.xml, /sitemap_index.xml,
    and robots.txt Sitemap directives. Validates entries for lastmod, changefreq, priority."""
    from mcp_seo.analyzers.sitemap import (
        analyze_sitemap as _analyze,
        format_sitemap_report,
    )

    url = _ensure_url(url)
    return format_sitemap_report(_analyze(url))


@mcp.tool()
def analyze_robots(url: str) -> str:
    """Fetch and analyze robots.txt: parses user-agent rules (Disallow/Allow),
    crawl-delay, sitemap directives. Detects blocking issues."""
    from mcp_seo.analyzers.robots import (
        analyze_robots as _analyze,
        format_robots_report,
    )

    url = _ensure_url(url)
    return format_robots_report(_analyze(url))


@mcp.tool()
def analyze_structured_data(url: str) -> str:
    """Extract and validate structured data: JSON-LD, Microdata, and RDFa.
    Parses and displays schema types, validates JSON syntax."""
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data as _analyze,
        format_structured_data_report,
    )

    html, _ = _get_html(url)
    return format_structured_data_report(_analyze(html))


# ── Tools: Performance ───────────────────────────────────────


@mcp.tool()
def analyze_performance(url: str) -> str:
    """Measure Core Web Vitals and page load metrics: TTFB, FCP, LCP,
    DOM Content Loaded, Load Event, DOM node count, total requests,
    transfer size, and resource breakdown by type."""
    from mcp_seo.analyzers.performance import (
        analyze_performance as _analyze,
        format_performance_report,
    )

    url = _ensure_url(url)
    return format_performance_report(_analyze(url))


@mcp.tool()
def analyze_mobile(url: str) -> str:
    """Analyze mobile-friendliness: viewport meta, responsive design detection,
    font sizes (< 12px check), tap target sizes (44x44px check),
    horizontal scroll, and media query detection."""
    from mcp_seo.analyzers.mobile import (
        analyze_mobile as _analyze,
        format_mobile_report,
    )

    url = _ensure_url(url)
    return format_mobile_report(_analyze(url))


# ── Tools: Reports ───────────────────────────────────────────


@mcp.tool()
def lighthouse_audit(url: str) -> str:
    """Run a Lighthouse-style SEO audit with category scores (0-100):
    Meta Tags, Heading Structure, Content Quality, Images, Structured Data.
    Returns overall score with pass/fail details."""
    from mcp_seo.analyzers.lighthouse import run_lighthouse, format_lighthouse_report

    html, final_url = _get_html(url)
    return format_lighthouse_report(run_lighthouse(html, final_url))


@mcp.tool()
def full_seo_report(url: str) -> str:
    """Generate a comprehensive SEO report combining ALL analyses:
    HTTP headers, meta tags, headings, links, images, structured data,
    content quality, and lighthouse scoring. This is the most complete analysis."""
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report
    from mcp_seo.analyzers.headings import (
        analyze_headings as _headings,
        format_headings_report,
    )
    from mcp_seo.analyzers.links import (
        analyze_links as _links,
        format_links_report,
    )
    from mcp_seo.analyzers.images import (
        analyze_images as _images,
        format_images_report,
    )
    from mcp_seo.analyzers.headers import (
        analyze_headers as _headers,
        format_headers_report,
    )
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data as _sd,
        format_structured_data_report,
    )
    from mcp_seo.analyzers.content import (
        analyze_content as _content,
        format_content_report,
    )
    from mcp_seo.analyzers.lighthouse import run_lighthouse, format_lighthouse_report

    url = _ensure_url(url)
    parts: list[str] = []
    parts.append(f"# Comprehensive SEO Report")
    parts.append(f"**URL**: {url}")
    parts.append(f"**Date**: {datetime.now().isoformat()}")
    parts.append("")

    # HTTP headers
    fetch_result = fetch(url)
    parts.append(
        format_headers_report(
            _headers(
                fetch_result.headers,
                fetch_result.status_code,
                fetch_result.redirect_chain,
            )
        )
    )

    # Render page
    html = render_page_sync(url)
    final_url = url

    parts.append(format_meta_report(analyze_meta(html, final_url)))
    parts.append(format_headings_report(_headings(html)))
    parts.append(format_links_report(_links(html, final_url)))
    parts.append(format_images_report(_images(html, final_url)))
    parts.append(format_structured_data_report(_sd(html)))
    parts.append(format_content_report(_content(html)))
    parts.append(format_lighthouse_report(run_lighthouse(html, final_url)))

    parts.append("---")
    parts.append("Report complete. Use individual tools for deeper analysis.")

    return "\n".join(parts)
