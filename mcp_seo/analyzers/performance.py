"""Performance analysis using headless browser metrics."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from mcp_seo.browser import get_browser, get_page


class PerformanceMetrics(BaseModel):
    """Core Web Vitals and other performance metrics."""

    url: str = ""
    ttfb_ms: float = 0  # Time to First Byte
    fcp_ms: float = 0  # First Contentful Paint
    lcp_ms: float = 0  # Largest Contentful Paint
    dom_content_loaded_ms: float = 0
    load_event_ms: float = 0
    total_requests: int = 0
    total_transfer_size_kb: float = 0
    total_resource_size_kb: float = 0
    dom_nodes: int = 0
    resource_breakdown: dict[str, int] = {}  # type -> count
    issues: list[str] = []


async def _measure_performance(url: str) -> PerformanceMetrics:
    """Measure page performance using Playwright."""
    result = PerformanceMetrics(url=url)
    issues: list[str] = []

    async with get_browser() as browser:
        async with get_page(browser) as page:
            # Track requests
            requests_count = 0
            resource_types: dict[str, int] = {}

            def on_request(request):
                nonlocal requests_count
                requests_count += 1
                rt = request.resource_type
                resource_types[rt] = resource_types.get(rt, 0) + 1

            page.on("request", on_request)

            # Navigate
            response = await page.goto(url, wait_until="networkidle", timeout=30000)

            if response:
                # TTFB from server timing
                timing = await page.evaluate("""() => {
                    const perf = performance.getEntriesByType('navigation')[0];
                    if (!perf) return null;
                    return {
                        ttfb: perf.responseStart - perf.requestStart,
                        domContentLoaded: perf.domContentLoadedEventEnd - perf.startTime,
                        loadEvent: perf.loadEventEnd - perf.startTime,
                        transferSize: perf.transferSize || 0,
                        domNodes: document.querySelectorAll('*').length,
                    };
                }""")

                if timing:
                    result.ttfb_ms = round(timing.get("ttfb", 0), 2)
                    result.dom_content_loaded_ms = round(
                        timing.get("domContentLoaded", 0), 2
                    )
                    result.load_event_ms = round(timing.get("loadEvent", 0), 2)
                    result.total_transfer_size_kb = round(
                        timing.get("transferSize", 0) / 1024, 2
                    )
                    result.dom_nodes = timing.get("domNodes", 0)

                # FCP
                fcp = await page.evaluate("""() => {
                    const entries = performance.getEntriesByName('first-contentful-paint');
                    return entries.length > 0 ? entries[0].startTime : 0;
                }""")
                result.fcp_ms = round(fcp, 2)

                # LCP
                lcp = await page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let lcpValue = 0;
                        const observer = new PerformanceObserver((list) => {
                            const entries = list.getEntries();
                            if (entries.length > 0) {
                                lcpValue = entries[entries.length - 1].startTime;
                            }
                        });
                        observer.observe({type: 'largest-contentful-paint', buffered: true});
                        setTimeout(() => {
                            observer.disconnect();
                            resolve(lcpValue);
                        }, 1000);
                    });
                }""")
                result.lcp_ms = round(lcp, 2)

                # Resource sizes
                resource_info = await page.evaluate("""() => {
                    const entries = performance.getEntriesByType('resource');
                    let totalSize = 0;
                    entries.forEach(e => { totalSize += e.transferSize || 0; });
                    return { totalSize, count: entries.length };
                }""")
                result.total_resource_size_kb = round(
                    resource_info.get("totalSize", 0) / 1024, 2
                )

            result.total_requests = requests_count
            result.resource_breakdown = resource_types

    # Evaluate performance
    if result.ttfb_ms > 800:
        issues.append(f"Slow TTFB: {result.ttfb_ms}ms (should be < 800ms)")
    if result.fcp_ms > 1800:
        issues.append(f"Slow FCP: {result.fcp_ms}ms (should be < 1800ms)")
    if result.lcp_ms > 2500:
        issues.append(f"Slow LCP: {result.lcp_ms}ms (should be < 2500ms)")
    if result.dom_nodes > 1500:
        issues.append(f"Excessive DOM nodes: {result.dom_nodes} (should be < 1500)")
    if result.total_requests > 80:
        issues.append(f"Too many requests: {result.total_requests} (should be < 80)")
    if result.total_resource_size_kb > 3000:
        issues.append(
            f"Large total page size: {result.total_resource_size_kb}KB (should be < 3000KB)"
        )

    result.issues = issues
    return result


def analyze_performance(url: str) -> PerformanceMetrics:
    """Measure and analyze page performance (sync wrapper)."""
    return asyncio.run(_measure_performance(url))


def format_performance_report(metrics: PerformanceMetrics) -> str:
    """Format performance metrics as a readable report."""
    lines = ["# Performance Analysis", ""]

    lines.append("## Core Web Vitals")
    lines.append(
        f"- **TTFB**: {metrics.ttfb_ms}ms {'✅' if metrics.ttfb_ms <= 800 else '❌'}"
    )
    lines.append(
        f"- **FCP**: {metrics.fcp_ms}ms {'✅' if metrics.fcp_ms <= 1800 else '❌'}"
    )
    lines.append(
        f"- **LCP**: {metrics.lcp_ms}ms {'✅' if metrics.lcp_ms <= 2500 else '❌'}"
    )
    lines.append("")

    lines.append("## Page Load")
    lines.append(f"- **DOM Content Loaded**: {metrics.dom_content_loaded_ms}ms")
    lines.append(f"- **Load Event**: {metrics.load_event_ms}ms")
    lines.append(f"- **DOM Nodes**: {metrics.dom_nodes}")
    lines.append("")

    lines.append("## Resources")
    lines.append(f"- **Total Requests**: {metrics.total_requests}")
    lines.append(f"- **Transfer Size**: {metrics.total_transfer_size_kb}KB")
    lines.append(f"- **Resource Size**: {metrics.total_resource_size_kb}KB")
    lines.append("")

    if metrics.resource_breakdown:
        lines.append("## Resource Breakdown")
        for rtype, count in sorted(
            metrics.resource_breakdown.items(), key=lambda x: -x[1]
        ):
            lines.append(f"- **{rtype}**: {count}")
        lines.append("")

    if metrics.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in metrics.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
