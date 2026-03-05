"""Mobile-friendliness analysis with interstitial detection and viewport checks."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from mcp_seo.browser import get_browser, get_page
from mcp_seo.utils import get_logger

logger = get_logger("mobile")


class MobileAnalysis(BaseModel):
    has_viewport_meta: bool = False
    viewport_content: str | None = None
    is_responsive: bool = False
    uses_media_queries: bool = False
    font_size_ok: bool = True
    tap_targets_ok: bool = True
    horizontal_scroll: bool = False

    # New checks
    pinch_zoom_disabled: bool = False
    has_interstitial: bool = False
    content_width_ok: bool = True
    small_text_count: int = 0
    small_text_total: int = 0
    small_target_count: int = 0
    small_target_total: int = 0

    issues: list[str] = []


async def _analyze_mobile(url: str) -> MobileAnalysis:
    """Analyze mobile-friendliness using headless browser."""
    result = MobileAnalysis()
    issues: list[str] = []

    # Mobile check
    async with get_browser() as browser, get_page(browser, mobile=True) as mobile_page:
        await mobile_page.goto(url, wait_until="networkidle", timeout=30000)

        # Check viewport meta
        viewport_info = await mobile_page.evaluate("""() => {
                const meta = document.querySelector('meta[name="viewport"]');
                if (!meta) return null;
                return {
                    content: meta.getAttribute('content'),
                };
            }""")

        if viewport_info:
            result.has_viewport_meta = True
            result.viewport_content = viewport_info["content"]
            content = viewport_info["content"].lower()

            if "width=device-width" not in content:
                issues.append("Viewport meta doesn't include width=device-width")

            # Check for pinch-zoom disabled
            if "user-scalable=no" in content or "maximum-scale=1" in content:
                result.pinch_zoom_disabled = True
                issues.append(
                    "Viewport disables pinch-to-zoom (user-scalable=no or maximum-scale=1). "
                    "This hurts accessibility and may affect rankings."
                )
        else:
            result.has_viewport_meta = False
            issues.append("CRITICAL: Missing viewport meta tag")

        # Check for horizontal scroll
        has_overflow = await mobile_page.evaluate("""() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }""")
        result.horizontal_scroll = has_overflow
        if has_overflow:
            issues.append("Page has horizontal scroll on mobile")

        # Check font sizes
        small_text = await mobile_page.evaluate("""() => {
                const elements = document.querySelectorAll('p, span, li, a, td, label, div');
                let smallCount = 0;
                let totalCount = 0;
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const fontSize = parseFloat(style.fontSize);
                    if (el.textContent.trim().length > 0 && el.offsetWidth > 0) {
                        totalCount++;
                        if (fontSize < 12) smallCount++;
                    }
                });
                return { smallCount, totalCount };
            }""")

        result.small_text_count = small_text["smallCount"]
        result.small_text_total = small_text["totalCount"]

        if small_text["totalCount"] > 0:
            ratio = small_text["smallCount"] / small_text["totalCount"]
            if ratio > 0.1:
                result.font_size_ok = False
                issues.append(
                    f"{small_text['smallCount']}/{small_text['totalCount']} text elements have font-size < 12px"
                )

        # Check tap target sizes (48x48dp recommended by Google)
        small_targets = await mobile_page.evaluate("""() => {
                const elements = document.querySelectorAll('a, button, input, select, textarea, [role="button"]');
                let smallCount = 0;
                let totalCount = 0;
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        totalCount++;
                        if (rect.width < 48 || rect.height < 48) {
                            smallCount++;
                        }
                    }
                });
                return { smallCount, totalCount };
            }""")

        result.small_target_count = small_targets["smallCount"]
        result.small_target_total = small_targets["totalCount"]

        if small_targets["totalCount"] > 0:
            ratio = small_targets["smallCount"] / small_targets["totalCount"]
            if ratio > 0.2:
                result.tap_targets_ok = False
                issues.append(
                    f"{small_targets['smallCount']}/{small_targets['totalCount']} "
                    "tap targets are smaller than 48x48dp (Google recommended minimum)"
                )

        # Check for intrusive interstitials
        has_interstitial = await mobile_page.evaluate("""() => {
                // Look for common interstitial/popup patterns
                const selectors = [
                    '[class*="modal"]', '[class*="popup"]', '[class*="overlay"]',
                    '[class*="interstitial"]', '[class*="cookie"]', '[class*="consent"]',
                    '[id*="modal"]', '[id*="popup"]', '[id*="overlay"]',
                    '[role="dialog"]', '[role="alertdialog"]',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        if (style.display !== 'none' && style.visibility !== 'hidden' &&
                            rect.width > window.innerWidth * 0.5 &&
                            rect.height > window.innerHeight * 0.3) {
                            return true;
                        }
                    }
                }
                return false;
            }""")
        result.has_interstitial = has_interstitial
        if has_interstitial:
            issues.append(
                "Intrusive interstitial/popup detected on mobile. "
                "Google may penalize pages with intrusive interstitials."
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

        # Check content width
        content_width_ok = await mobile_page.evaluate("""() => {
                const body = document.body;
                const imgs = document.querySelectorAll('img');
                const tables = document.querySelectorAll('table');
                const vw = window.innerWidth;

                for (const img of imgs) {
                    if (img.naturalWidth > vw && !img.style.maxWidth) {
                        return false;
                    }
                }
                for (const table of tables) {
                    if (table.scrollWidth > vw) return false;
                }
                return true;
            }""")
        result.content_width_ok = content_width_ok
        if not content_width_ok:
            issues.append("Some content (images/tables) is wider than the mobile viewport")

    # Determine if responsive
    result.is_responsive = (
        result.has_viewport_meta
        and not result.horizontal_scroll
        and result.font_size_ok
        and result.content_width_ok
        and not result.pinch_zoom_disabled
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

    lines.append(f"**Responsive**: {'Yes' if analysis.is_responsive else 'No'}")
    lines.append(f"**Viewport Meta**: {'Present' if analysis.has_viewport_meta else 'Missing'}")
    if analysis.viewport_content:
        lines.append(f"  - Content: `{analysis.viewport_content}`")
    lines.append(f"**Media Queries**: {'Found' if analysis.uses_media_queries else 'Not found'}")
    lines.append(f"**Font Sizes OK**: {'Yes' if analysis.font_size_ok else 'No'}")
    if analysis.small_text_total > 0:
        lines.append(f"  - Small text: {analysis.small_text_count}/{analysis.small_text_total}")
    lines.append(f"**Tap Targets OK**: {'Yes' if analysis.tap_targets_ok else 'No'}")
    if analysis.small_target_total > 0:
        lines.append(f"  - Small targets: {analysis.small_target_count}/{analysis.small_target_total}")
    lines.append(f"**Horizontal Scroll**: {'Yes (bad)' if analysis.horizontal_scroll else 'No'}")
    lines.append(f"**Pinch-Zoom Disabled**: {'Yes (bad)' if analysis.pinch_zoom_disabled else 'No'}")
    lines.append(f"**Intrusive Interstitial**: {'Detected' if analysis.has_interstitial else 'None'}")
    lines.append(f"**Content Width OK**: {'Yes' if analysis.content_width_ok else 'No'}")
    lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
