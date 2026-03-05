"""MCP-SEO Server — exposes all SEO tools as MCP tools."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from mcp_seo.browser import render_page_sync
from mcp_seo.fetcher import fetch
from mcp_seo.utils import ensure_url, get_html, get_logger

logger = get_logger("mcp_server")

mcp = FastMCP(
    "MCP-SEO",
    instructions=(
        "MCP-SEO is an open-source SEO analysis toolkit for AI agents. "
        "Use these tools to audit any webpage for on-page SEO, "
        "technical SEO, performance, mobile-friendliness, and more. "
        "All tools accept a URL and return Markdown-formatted reports."
    ),
)


# ── Tools: Page Fetching ─────────────────────────────────────


@mcp.tool()
def crawl(url: str) -> str:
    """Render a page with headless Chromium and return the full rendered HTML.
    Use this when the page is a SPA or uses client-side rendering."""
    url = ensure_url(url)
    return render_page_sync(url)


@mcp.tool()
def fetch_page(url: str) -> str:
    """Fetch the raw HTTP response without JS rendering.
    Returns JSON with status code, headers, body, redirect chain, and timing."""
    url = ensure_url(url)
    result = fetch(url)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


# ── Tools: On-Page SEO ───────────────────────────────────────


@mcp.tool()
def analyze_meta_tags(url: str) -> str:
    """Analyze meta tags: title (with pixel-width estimation), meta description,
    canonical (self-referencing check), robots, viewport, charset, lang,
    Open Graph tags, Twitter Card tags, hreflang tags, and favicon."""
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report

    html, final_url = get_html(url)
    return format_meta_report(analyze_meta(html, final_url))


@mcp.tool()
def analyze_headings(url: str) -> str:
    """Extract and validate the heading hierarchy (h1-h6).
    Checks for single H1, skipped levels, empty headings,
    duplicate headings, and long headings (>70 chars)."""
    from mcp_seo.analyzers.headings import (
        analyze_headings as _analyze,
    )
    from mcp_seo.analyzers.headings import (
        format_headings_report,
    )

    html, _ = get_html(url)
    return format_headings_report(_analyze(html))


@mcp.tool()
def analyze_links(url: str, check_broken: bool = False) -> str:
    """Analyze all links on a page: internal vs external count,
    nofollow/sponsored/ugc detection, anchor text analysis,
    pagination detection, follow ratio, and optional broken link checking."""
    from mcp_seo.analyzers.links import (
        analyze_links as _analyze,
    )
    from mcp_seo.analyzers.links import (
        format_links_report,
    )

    html, final_url = get_html(url)
    return format_links_report(_analyze(html, final_url, check_broken=check_broken))


@mcp.tool()
def analyze_images(url: str) -> str:
    """Audit images: alt text presence, lazy loading, explicit dimensions
    (width/height for CLS), modern format usage (WebP/AVIF), srcset and
    picture element analysis."""
    from mcp_seo.analyzers.images import (
        analyze_images as _analyze,
    )
    from mcp_seo.analyzers.images import (
        format_images_report,
    )

    html, final_url = get_html(url)
    return format_images_report(_analyze(html, final_url))


@mcp.tool()
def analyze_content(url: str) -> str:
    """Analyze page content: word count, Flesch-Kincaid readability score,
    reading grade level, keyword density, sentence analysis, text-to-HTML
    ratio, top keywords, bigrams, trigrams, and keyword stuffing detection."""
    from mcp_seo.analyzers.content import (
        analyze_content as _analyze,
    )
    from mcp_seo.analyzers.content import (
        format_content_report,
    )

    html, _ = get_html(url)
    return format_content_report(_analyze(html))


# ── Tools: Technical SEO ─────────────────────────────────────


@mcp.tool()
def analyze_headers(url: str) -> str:
    """Inspect HTTP response headers: caching (Cache-Control, ETag),
    security (HSTS with max-age validation, CSP, X-Frame-Options),
    SSL certificate validation, cookie security (Secure/HttpOnly/SameSite),
    compression, server info, and redirect chain analysis."""
    from mcp_seo.analyzers.headers import (
        analyze_headers as _analyze,
    )
    from mcp_seo.analyzers.headers import (
        format_headers_report,
    )

    url = ensure_url(url)
    result = fetch(url)
    return format_headers_report(
        _analyze(
            result.headers,
            result.status_code,
            result.redirect_chain,
            ssl_valid=result.ssl_valid,
            ssl_error=result.ssl_error,
            http_version=result.http_version,
        )
    )


@mcp.tool()
def analyze_sitemap(url: str) -> str:
    """Discover and parse XML sitemaps: checks /sitemap.xml, /sitemap_index.xml,
    and robots.txt Sitemap directives. Validates URL count limits (50K),
    file size (50MB), lastmod format (W3C), and freshness."""
    from mcp_seo.analyzers.sitemap import (
        analyze_sitemap as _analyze,
    )
    from mcp_seo.analyzers.sitemap import (
        format_sitemap_report,
    )

    url = ensure_url(url)
    return format_sitemap_report(_analyze(url))


@mcp.tool()
def analyze_robots(url: str) -> str:
    """Fetch and analyze robots.txt: parses user-agent rules (Disallow/Allow),
    crawl-delay, sitemap directives. Detects blocking of important bots
    (Googlebot, Bingbot), CSS/JS resource blocking, contradictory rules,
    and file size limits."""
    from mcp_seo.analyzers.robots import (
        analyze_robots as _analyze,
    )
    from mcp_seo.analyzers.robots import (
        format_robots_report,
    )

    url = ensure_url(url)
    return format_robots_report(_analyze(url))


@mcp.tool()
def analyze_structured_data(url: str) -> str:
    """Extract and validate structured data: JSON-LD, Microdata, and RDFa.
    Validates Schema.org required properties, checks Rich Result eligibility,
    detects @context and @graph handling, and recommends WebSite/Organization schemas."""
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data as _analyze,
    )
    from mcp_seo.analyzers.structured_data import (
        format_structured_data_report,
    )

    html, _ = get_html(url)
    return format_structured_data_report(_analyze(html))


# ── Tools: Performance ───────────────────────────────────────


@mcp.tool()
def analyze_performance(url: str) -> str:
    """Measure all Core Web Vitals: TTFB, FCP, LCP, CLS (Cumulative Layout Shift),
    TBT (Total Blocking Time), DOM nodes, total requests, transfer size,
    render-blocking resources, and resource breakdown by type."""
    from mcp_seo.analyzers.performance import (
        analyze_performance as _analyze,
    )
    from mcp_seo.analyzers.performance import (
        format_performance_report,
    )

    url = ensure_url(url)
    return format_performance_report(_analyze(url))


@mcp.tool()
def analyze_mobile(url: str) -> str:
    """Analyze mobile-friendliness: viewport meta, responsive design detection,
    font sizes (<12px check), tap target sizes (48x48dp check), horizontal scroll,
    pinch-to-zoom disabled check, intrusive interstitial detection,
    and content width validation."""
    from mcp_seo.analyzers.mobile import (
        analyze_mobile as _analyze,
    )
    from mcp_seo.analyzers.mobile import (
        format_mobile_report,
    )

    url = ensure_url(url)
    return format_mobile_report(_analyze(url))


# ── Tools: URL Structure & Accessibility ─────────────────────


@mcp.tool()
def analyze_url_structure(url: str) -> str:
    """Analyze URL structure for SEO best practices: length, depth,
    separator usage (hyphens vs underscores), uppercase detection,
    tracking parameter detection, session ID detection, file extensions,
    and path keyword extraction."""
    from mcp_seo.analyzers.url_structure import (
        analyze_url_structure as _analyze,
    )
    from mcp_seo.analyzers.url_structure import (
        format_url_structure_report,
    )

    url = ensure_url(url)
    return format_url_structure_report(_analyze(url))


@mcp.tool()
def analyze_accessibility(url: str) -> str:
    """Analyze page accessibility: ARIA landmarks (main, nav, banner),
    skip navigation links, ARIA roles/labels, image alt text audit,
    form input labeling, table headers, link accessible text,
    and focus management (tabindex). Returns a score out of 100."""
    from mcp_seo.analyzers.accessibility import (
        analyze_accessibility as _analyze,
    )
    from mcp_seo.analyzers.accessibility import (
        format_accessibility_report,
    )

    html, _ = get_html(url)
    return format_accessibility_report(_analyze(html))


# ── Tools: Reports ───────────────────────────────────────────


@mcp.tool()
def lighthouse_audit(url: str) -> str:
    """Run a comprehensive SEO audit with weighted continuous scoring (0-100):
    Meta Tags, Heading Structure, Content Quality, Images, Structured Data, Links.
    Returns overall score with individual check scores and severity-prioritized issues."""
    from mcp_seo.analyzers.lighthouse import format_lighthouse_report, run_lighthouse

    html, final_url = get_html(url)
    return format_lighthouse_report(run_lighthouse(html, final_url))


@mcp.tool()
def full_seo_report(url: str) -> str:
    """Generate a comprehensive SEO report combining ALL analyses:
    HTTP headers, SSL validation, meta tags, headings, links, images,
    structured data, content quality, sitemap, robots.txt, performance
    (Core Web Vitals), mobile-friendliness, and lighthouse scoring.
    This is the most complete analysis available."""
    from mcp_seo.report import generate_full_report

    markdown, _results = generate_full_report(url)
    return markdown


@mcp.tool()
def crawl_site(url: str, max_pages: int = 50) -> str:
    """Crawl a website discovering pages via internal links.
    Analyzes each page for meta tags, headings, and common SEO issues.
    Returns a site-wide summary with cross-page duplicate detection."""
    from mcp_seo.crawler import crawl_site as _crawl
    from mcp_seo.crawler import format_crawl_report

    url = ensure_url(url)
    result = _crawl(url, max_pages=max_pages)
    return format_crawl_report(result)
