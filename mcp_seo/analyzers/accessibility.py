"""Accessibility analysis: ARIA, landmarks, skip-nav, heading order, forms, tables."""

from __future__ import annotations

from pydantic import BaseModel

from mcp_seo.utils import get_logger, parse_html

logger = get_logger("accessibility")


class AccessibilityAnalysis(BaseModel):
    """Result of accessibility analysis."""

    # Landmarks
    has_main_landmark: bool = False
    has_nav_landmark: bool = False
    has_banner_landmark: bool = False
    has_contentinfo_landmark: bool = False
    landmark_count: int = 0

    # Skip navigation
    has_skip_nav: bool = False

    # ARIA
    aria_roles_found: list[str] = []
    aria_labels_count: int = 0
    aria_describedby_count: int = 0
    aria_hidden_count: int = 0

    # Images
    images_total: int = 0
    images_with_alt: int = 0
    images_empty_alt: int = 0  # Decorative (alt="")
    images_missing_alt: int = 0

    # Forms
    form_inputs_total: int = 0
    form_inputs_with_label: int = 0
    form_inputs_without_label: int = 0

    # Tables
    tables_total: int = 0
    tables_with_caption: int = 0
    tables_with_headers: int = 0

    # Links
    links_total: int = 0
    links_with_text: int = 0
    links_without_text: int = 0
    links_new_window_no_warning: int = 0

    # Language
    has_lang_attribute: bool = False
    lang_value: str | None = None

    # Focus
    tabindex_negative_count: int = 0

    issues: list[str] = []
    score: int = 0  # 0-100


def analyze_accessibility(html: str) -> AccessibilityAnalysis:
    """Analyze HTML for accessibility best practices."""
    soup = parse_html(html)
    result = AccessibilityAnalysis()
    issues: list[str] = []

    # ── Language ──────────────────────────────────────────────
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        result.has_lang_attribute = True
        result.lang_value = str(html_tag["lang"])
    else:
        issues.append("CRITICAL: Missing lang attribute on <html> tag")

    # ── Landmarks ─────────────────────────────────────────────
    # Check both HTML5 elements and ARIA roles
    landmark_map = {
        "main": ["main", "[role='main']"],
        "nav": ["nav", "[role='navigation']"],
        "banner": ["header", "[role='banner']"],
        "contentinfo": ["footer", "[role='contentinfo']"],
    }

    for landmark_type, selectors in landmark_map.items():
        found = False
        for sel in selectors:
            if soup.select(sel):
                found = True
                break
        if found:
            result.landmark_count += 1
            if landmark_type == "main":
                result.has_main_landmark = True
            elif landmark_type == "nav":
                result.has_nav_landmark = True
            elif landmark_type == "banner":
                result.has_banner_landmark = True
            elif landmark_type == "contentinfo":
                result.has_contentinfo_landmark = True

    if not result.has_main_landmark:
        issues.append("Missing <main> landmark or role='main'")
    if not result.has_nav_landmark:
        issues.append("Missing <nav> landmark or role='navigation'")

    # ── Skip navigation ───────────────────────────────────────
    # Look for a link early in the document that jumps to main content
    first_links = soup.find_all("a", limit=5)
    for link in first_links:
        href = str(link.get("href", ""))
        text = link.get_text(strip=True).lower()
        if href.startswith("#") and any(kw in text for kw in ("skip", "main content", "jump to", "contenuto")):
            result.has_skip_nav = True
            break

    if not result.has_skip_nav:
        issues.append("No skip navigation link found (helps keyboard users)")

    # ── ARIA ──────────────────────────────────────────────────
    roles = set()
    for el in soup.find_all(attrs={"role": True}):
        roles.add(str(el["role"]))
    result.aria_roles_found = sorted(roles)

    result.aria_labels_count = len(soup.find_all(attrs={"aria-label": True}))
    result.aria_describedby_count = len(soup.find_all(attrs={"aria-describedby": True}))
    result.aria_hidden_count = len(soup.find_all(attrs={"aria-hidden": "true"}))

    # ── Images ────────────────────────────────────────────────
    imgs = soup.find_all("img")
    result.images_total = len(imgs)
    for img in imgs:
        alt = img.get("alt")
        if alt is None:
            result.images_missing_alt += 1
        elif alt == "":
            result.images_empty_alt += 1  # Decorative
        else:
            result.images_with_alt += 1

    if result.images_missing_alt > 0:
        issues.append(f"CRITICAL: {result.images_missing_alt} image(s) missing alt attribute")

    # ── Forms ─────────────────────────────────────────────────
    inputs = soup.find_all(["input", "select", "textarea"])
    # Exclude hidden/submit/button types
    meaningful_inputs = [
        inp
        for inp in inputs
        if str(inp.get("type", "")).lower() not in ("hidden", "submit", "button", "image", "reset")
    ]
    result.form_inputs_total = len(meaningful_inputs)

    for inp in meaningful_inputs:
        inp_id = inp.get("id")
        has_label = False

        # Check for associated <label>
        if inp_id:
            label = soup.find("label", attrs={"for": inp_id})
            if label:
                has_label = True

        # Check for aria-label or aria-labelledby
        if inp.get("aria-label") or inp.get("aria-labelledby"):
            has_label = True

        # Check for wrapping <label>
        if inp.find_parent("label"):
            has_label = True

        # Check for title attribute (fallback)
        if inp.get("title"):
            has_label = True

        if has_label:
            result.form_inputs_with_label += 1
        else:
            result.form_inputs_without_label += 1

    if result.form_inputs_without_label > 0:
        issues.append(f"{result.form_inputs_without_label} form input(s) without associated label")

    # ── Tables ────────────────────────────────────────────────
    tables = soup.find_all("table")
    result.tables_total = len(tables)
    for table in tables:
        if table.find("caption"):
            result.tables_with_caption += 1
        if table.find("th"):
            result.tables_with_headers += 1

    if result.tables_total > 0 and result.tables_with_headers == 0:
        issues.append("Table(s) found without header cells (<th>)")

    # ── Links ─────────────────────────────────────────────────
    all_links = soup.find_all("a")
    result.links_total = len(all_links)
    for link in all_links:
        text = link.get_text(strip=True)
        img = link.find("img")
        aria_label = link.get("aria-label")

        if text or (img and img.get("alt")) or aria_label:
            result.links_with_text += 1
        else:
            result.links_without_text += 1

        # Check for target="_blank" without warning
        if str(link.get("target", "")).lower() == "_blank" and (not aria_label or "new" not in aria_label.lower()):
            result.links_new_window_no_warning += 1

    if result.links_without_text > 0:
        issues.append(f"{result.links_without_text} link(s) without accessible text")

    if result.links_new_window_no_warning > 3:
        issues.append(
            f"{result.links_new_window_no_warning} links open in new window "
            "without warning (add aria-label or visual indicator)"
        )

    # ── Focus management ──────────────────────────────────────
    negative_tabindex = soup.find_all(attrs={"tabindex": True})
    for el in negative_tabindex:
        try:
            if int(el["tabindex"]) < 0:
                result.tabindex_negative_count += 1
        except (ValueError, TypeError):
            pass

    if result.tabindex_negative_count > 5:
        issues.append(
            f"{result.tabindex_negative_count} elements with tabindex='-1' "
            "(may be removing content from keyboard navigation)"
        )

    # ── Scoring ───────────────────────────────────────────────
    checks_passed = 0
    total_checks = 10

    if result.has_lang_attribute:
        checks_passed += 1
    if result.has_main_landmark:
        checks_passed += 1
    if result.has_nav_landmark:
        checks_passed += 1
    if result.has_skip_nav:
        checks_passed += 1
    if result.images_missing_alt == 0:
        checks_passed += 1
    if result.form_inputs_without_label == 0:
        checks_passed += 1
    if result.links_without_text == 0:
        checks_passed += 1
    if result.tables_total == 0 or result.tables_with_headers > 0:
        checks_passed += 1
    if result.aria_labels_count > 0 or result.aria_roles_found:
        checks_passed += 1
    if result.tabindex_negative_count <= 5:
        checks_passed += 1

    result.score = round(checks_passed / total_checks * 100)
    result.issues = issues
    return result


def format_accessibility_report(analysis: AccessibilityAnalysis) -> str:
    """Format accessibility analysis as a readable report."""
    lines = ["# Accessibility Analysis", ""]
    lines.append(f"**Score**: {analysis.score}/100")
    lines.append("")

    lines.append("## Landmarks")
    lines.append(f"- **<main>**: {'Yes' if analysis.has_main_landmark else 'MISSING'}")
    lines.append(f"- **<nav>**: {'Yes' if analysis.has_nav_landmark else 'MISSING'}")
    lines.append(f"- **<header>**: {'Yes' if analysis.has_banner_landmark else 'MISSING'}")
    lines.append(f"- **<footer>**: {'Yes' if analysis.has_contentinfo_landmark else 'MISSING'}")
    lines.append(f"- **Skip navigation**: {'Yes' if analysis.has_skip_nav else 'No'}")
    lines.append("")

    lines.append("## ARIA Usage")
    lines.append(f"- **Roles found**: {', '.join(analysis.aria_roles_found) or 'None'}")
    lines.append(f"- **aria-label count**: {analysis.aria_labels_count}")
    lines.append(f"- **aria-describedby count**: {analysis.aria_describedby_count}")
    lines.append(f"- **aria-hidden count**: {analysis.aria_hidden_count}")
    lines.append("")

    if analysis.images_total > 0:
        lines.append("## Images")
        lines.append(f"- **Total**: {analysis.images_total}")
        lines.append(f"- **With alt text**: {analysis.images_with_alt}")
        lines.append(f"- **Decorative (alt='')**: {analysis.images_empty_alt}")
        lines.append(f"- **Missing alt**: {analysis.images_missing_alt}")
        lines.append("")

    if analysis.form_inputs_total > 0:
        lines.append("## Forms")
        lines.append(f"- **Total inputs**: {analysis.form_inputs_total}")
        lines.append(f"- **With label**: {analysis.form_inputs_with_label}")
        lines.append(f"- **Without label**: {analysis.form_inputs_without_label}")
        lines.append("")

    if analysis.tables_total > 0:
        lines.append("## Tables")
        lines.append(f"- **Total**: {analysis.tables_total}")
        lines.append(f"- **With caption**: {analysis.tables_with_caption}")
        lines.append(f"- **With headers (<th>)**: {analysis.tables_with_headers}")
        lines.append("")

    lines.append("## Links")
    lines.append(f"- **Total**: {analysis.links_total}")
    lines.append(f"- **With accessible text**: {analysis.links_with_text}")
    lines.append(f"- **Without accessible text**: {analysis.links_without_text}")
    if analysis.links_new_window_no_warning > 0:
        lines.append(f"- **Opens new window (no warning)**: {analysis.links_new_window_no_warning}")
    lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            if issue.startswith("CRITICAL"):
                lines.append(f"- **CRITICAL** {issue}")
            else:
                lines.append(f"- **WARNING** {issue}")
        lines.append("")

    return "\n".join(lines)
