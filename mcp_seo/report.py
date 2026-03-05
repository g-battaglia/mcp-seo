"""Shared full-report assembly — used by both CLI and MCP server."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from mcp_seo.utils import clear_soup_cache, ensure_url, get_logger

logger = get_logger("report")


class FullReportResult(BaseModel):
    """Container for all analysis results."""

    url: str
    date: str
    headers: Any = None
    meta: Any = None
    headings: Any = None
    links: Any = None
    images: Any = None
    structured_data: Any = None
    content: Any = None
    sitemap: Any = None
    robots: Any = None
    performance: Any = None
    mobile: Any = None
    lighthouse: Any = None


def _build_executive_summary(results: FullReportResult) -> str:
    """Build an executive summary section from all analysis results."""
    lines = ["## Executive Summary", ""]

    # Lighthouse score
    if results.lighthouse:
        score = results.lighthouse.overall_score
        if score >= 90:
            verdict = "Excellent"
        elif score >= 70:
            verdict = "Good"
        elif score >= 50:
            verdict = "Needs Improvement"
        else:
            verdict = "Poor"
        lines.append(f"**Overall SEO Score**: {score}/100 ({verdict})")
        lines.append("")

    # Collect all issues across analyzers
    critical: list[str] = []
    warnings: list[str] = []
    for field in (
        "meta",
        "headings",
        "links",
        "images",
        "content",
        "structured_data",
        "sitemap",
        "robots",
        "headers",
        "performance",
        "mobile",
    ):
        analyzer_result = getattr(results, field, None)
        if analyzer_result and hasattr(analyzer_result, "issues"):
            for issue in analyzer_result.issues:
                if "CRITICAL" in issue:
                    critical.append(issue)
                else:
                    warnings.append(issue)

    lines.append(f"**Critical Issues**: {len(critical)}")
    lines.append(f"**Warnings**: {len(warnings)}")
    lines.append("")

    # Key metrics
    if results.meta:
        lines.append("### Key Findings")
        title_status = "Present" if results.meta.title else "MISSING"
        desc_status = "Present" if results.meta.description else "MISSING"
        lines.append(f"- **Title**: {title_status}")
        lines.append(f"- **Description**: {desc_status}")
        if results.meta.canonical:
            lines.append(
                f"- **Canonical**: {'Self-referencing' if results.meta.canonical_is_self else 'Points elsewhere'}"
            )

    if results.content:
        lines.append(f"- **Word Count**: {results.content.word_count}")

    if results.performance:
        lines.append(f"- **LCP**: {results.performance.lcp_ms}ms")
        lines.append(f"- **CLS**: {results.performance.cls_score}")

    if results.links:
        lines.append(f"- **Internal Links**: {len(results.links.internal_links)}")
        lines.append(f"- **Broken Links**: {len(results.links.broken_links)}")

    lines.append("")

    # Top priorities
    if critical:
        lines.append("### Top Priorities")
        for issue in critical[:5]:
            lines.append(f"1. {issue}")
        lines.append("")

    return "\n".join(lines)


def generate_full_report(
    url: str,
    *,
    include_performance: bool = True,
    include_mobile: bool = True,
    progress_callback: Any | None = None,
) -> tuple[str, FullReportResult]:
    """Run all analyzers and return (markdown_report, raw_results).

    Args:
        url: The URL to analyze.
        include_performance: Run Core Web Vitals measurement (requires browser).
        include_mobile: Run mobile-friendliness check (requires browser).
        progress_callback: Optional callable(message: str) for status updates.

    Returns:
        Tuple of (markdown string, FullReportResult with all raw models).
    """
    from mcp_seo.analyzers.content import analyze_content, format_content_report
    from mcp_seo.analyzers.headers import analyze_headers, format_headers_report
    from mcp_seo.analyzers.headings import analyze_headings, format_headings_report
    from mcp_seo.analyzers.images import analyze_images, format_images_report
    from mcp_seo.analyzers.lighthouse import format_lighthouse_report, run_lighthouse
    from mcp_seo.analyzers.links import analyze_links, format_links_report
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report
    from mcp_seo.analyzers.mobile import analyze_mobile, format_mobile_report
    from mcp_seo.analyzers.performance import (
        analyze_performance,
        format_performance_report,
    )
    from mcp_seo.analyzers.robots import analyze_robots, format_robots_report
    from mcp_seo.analyzers.sitemap import analyze_sitemap, format_sitemap_report
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data,
        format_structured_data_report,
    )
    from mcp_seo.browser import render_page_sync
    from mcp_seo.fetcher import fetch

    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    url = ensure_url(url)
    report_date = datetime.now().isoformat()

    parts: list[str] = [
        "# Comprehensive SEO Report",
        f"**URL**: {url}",
        f"**Date**: {report_date}",
        "",
    ]

    results = FullReportResult(url=url, date=report_date)

    # 1. HTTP headers + SSL
    _progress("Analyzing HTTP headers...")
    fetch_result = fetch(url)
    headers_result = analyze_headers(
        fetch_result.headers,
        fetch_result.status_code,
        fetch_result.redirect_chain,
        ssl_valid=fetch_result.ssl_valid,
        ssl_error=fetch_result.ssl_error,
        http_version=fetch_result.http_version,
    )
    results.headers = headers_result
    parts.append(format_headers_report(headers_result))

    # 2. Render page (single render for all static analyzers)
    _progress("Rendering page with headless browser...")
    html = render_page_sync(url)
    final_url = url

    # 3. On-page analyzers (reuse same HTML)
    _progress("Analyzing on-page SEO...")
    results.meta = analyze_meta(html, final_url)
    results.headings = analyze_headings(html)
    results.links = analyze_links(html, final_url)
    results.images = analyze_images(html, final_url)
    results.structured_data = analyze_structured_data(html)
    results.content = analyze_content(html)

    parts.append(format_meta_report(results.meta))
    parts.append(format_headings_report(results.headings))
    parts.append(format_links_report(results.links))
    parts.append(format_images_report(results.images))
    parts.append(format_structured_data_report(results.structured_data))
    parts.append(format_content_report(results.content))

    # 4. Technical SEO (separate fetches)
    _progress("Analyzing sitemap and robots.txt...")
    results.sitemap = analyze_sitemap(url)
    results.robots = analyze_robots(url)
    parts.append(format_sitemap_report(results.sitemap))
    parts.append(format_robots_report(results.robots))

    # 5. Performance (separate browser session)
    if include_performance:
        _progress("Measuring performance (Core Web Vitals)...")
        results.performance = analyze_performance(url)
        parts.append(format_performance_report(results.performance))

    # 6. Mobile (separate browser session)
    if include_mobile:
        _progress("Checking mobile-friendliness...")
        results.mobile = analyze_mobile(url)
        parts.append(format_mobile_report(results.mobile))

    # 7. Lighthouse score
    _progress("Calculating SEO score...")
    results.lighthouse = run_lighthouse(html, final_url)
    parts.append(format_lighthouse_report(results.lighthouse))

    # 8. Executive Summary (prepended after header)
    summary = _build_executive_summary(results)
    # Insert after the header block (first 4 items: title, url, date, blank)
    parts.insert(4, summary)

    parts.append("---")
    parts.append("Report complete.")

    clear_soup_cache()

    return "\n".join(parts), results
