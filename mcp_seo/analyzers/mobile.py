"""Mobile-friendliness analysis."""

from __future__ import annotations

import asyncio
import re

from bs4 import BeautifulSoup
from pydantic import BaseModel

from mcp_seo.browser import get_browser, get_page


class MobileAnalysis(BaseModel):
    has_viewport_meta: bool = False
    viewport_content: str | None = None
    is_responsive: bool = False
    uses_media_queries: bool = False
    font_size_ok: bool = True
    tap_targets_ok: bool = True
    horizontal_scroll: bool = False
    mobile_screenshot_path: str | None = None
    issues: list[str] = []


async def _analyze_mobile(url: str) -> MobileAnalysis:
    """Analyze mobile-friendliness using headless browser."""
    result = MobileAnalysis()
    issues: list[str] = []

    async with get_browser() as browser:
        # First check with desktop
        async with get_page(browser) as desktop_page:
            await desktop_page.goto(url, wait_until="networkidle", timeout=30000)
            desktop_html = await desktop_page.content()

        # Then check with mobile
        async with get_page(browser, mobile=True) as mobile_page:
            await mobile_page.goto(url, wait_until="networkidle", timeout=30000)

            # Check viewport meta
            viewport = await mobile_page.evaluate("""() => {
                const meta = document.querySelector('meta[name="viewport"]');
                return meta ? meta.getAttribute('content') : null;
            }""")

            if viewport:
                result.has_viewport_meta = True
                result.viewport_content = viewport
                if "width=device-width" not in viewport:
                    issues.append("Viewport meta doesn't include width=device-width")
            else:
                result.has_viewport_meta = False
                issues.append("Missing viewport meta tag")

            # Check for horizontal scroll
            has_overflow = await mobile_page.evaluate("""() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }""")
            result.horizontal_scroll = has_overflow
            if has_overflow:
                issues.append("Page has horizontal scroll on mobile")

            # Check font sizes
            small_text = await mobile_page.evaluate("""() => {
                const elements = document.querySelectorAll('p, span, li, a, td');
                let smallCount = 0;
                let totalCount = 0;
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const fontSize = parseFloat(style.fontSize);
                    if (el.textContent.trim().length > 0) {
                        totalCount++;
                        if (fontSize < 12) smallCount++;
                    }
                });
                return { smallCount, totalCount };
            }""")

            if small_text["totalCount"] > 0:
                ratio = small_text["smallCount"] / small_text["totalCount"]
                if ratio > 0.1:
                    result.font_size_ok = False
                    issues.append(
                        f"{small_text['smallCount']}/{small_text['totalCount']} "
                        "text elements have font-size < 12px"
                    )

            # Check tap target sizes
            small_targets = await mobile_page.evaluate("""() => {
                const elements = document.querySelectorAll('a, button, input, select, textarea');
                let smallCount = 0;
                let totalCount = 0;
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        totalCount++;
                        if (rect.width < 44 || rect.height < 44) {
                            smallCount++;
                        }
                    }
                });
                return { smallCount, totalCount };
            }""")

            if small_targets["totalCount"] > 0:
                ratio = small_targets["smallCount"] / small_targets["totalCount"]
                if ratio > 0.3:
                    result.tap_targets_ok = False
                    issues.append(
                        f"{small_targets['smallCount']}/{small_targets['totalCount']} "
                        "tap targets are smaller than 44x44px"
                    )

            # Check for media queries in stylesheets
            has_media_queries = await mobile_page.evaluate("""() => {
                for (const sheet of document.styleSheets) {
                    try {
                        for (const rule of sheet.cssRules) {
                            if (rule instanceof CSSMediaRule) return true;
                        }
                    } catch(e) {}
                }
                return false;
            }""")
            result.uses_media_queries = has_media_queries

    # Determine if responsive
    result.is_responsive = (
        result.has_viewport_meta
        and not result.horizontal_scroll
        and result.font_size_ok
    )

    if not result.is_responsive:
        issues.append("Page may not be mobile-friendly")

    result.issues = issues
    return result


def analyze_mobile(url: str) -> MobileAnalysis:
    """Analyze mobile-friendliness (sync wrapper)."""
    return asyncio.run(_analyze_mobile(url))


def format_mobile_report(analysis: MobileAnalysis) -> str:
    """Format mobile analysis as a readable report."""
    lines = ["# Mobile-Friendliness Analysis", ""]

    lines.append(f"**Responsive**: {'✅ Yes' if analysis.is_responsive else '❌ No'}")
    lines.append(f"**Viewport Meta**: {'✅' if analysis.has_viewport_meta else '❌'}")
    if analysis.viewport_content:
        lines.append(f"  - Content: `{analysis.viewport_content}`")
    lines.append(
        f"**Media Queries**: {'✅ Found' if analysis.uses_media_queries else '❌ Not found'}"
    )
    lines.append(f"**Font Sizes OK**: {'✅' if analysis.font_size_ok else '❌'}")
    lines.append(f"**Tap Targets OK**: {'✅' if analysis.tap_targets_ok else '❌'}")
    lines.append(
        f"**Horizontal Scroll**: {'❌ Yes (bad)' if analysis.horizontal_scroll else '✅ No'}"
    )
    lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
