"""Lighthouse-style comprehensive SEO audit with weighted continuous scoring."""

from __future__ import annotations

from pydantic import BaseModel

from mcp_seo.analyzers.content import ContentAnalysis, analyze_content
from mcp_seo.analyzers.headings import HeadingsAnalysis, analyze_headings
from mcp_seo.analyzers.images import ImagesAnalysis, analyze_images
from mcp_seo.analyzers.links import LinksAnalysis, analyze_links
from mcp_seo.analyzers.meta import MetaAnalysis, analyze_meta
from mcp_seo.analyzers.structured_data import (
    StructuredDataAnalysis,
    analyze_structured_data,
)
from mcp_seo.utils import get_logger

logger = get_logger("lighthouse")


# ── Models ────────────────────────────────────────────────────


class AuditCheck(BaseModel):
    """A single audit check with weight and continuous score."""

    name: str
    passed: bool
    score: float = 0.0  # 0.0 - 1.0
    weight: float = 1.0
    detail: str = ""


class LighthouseCategory(BaseModel):
    category: str
    score: int = 0  # 0-100
    weight: float = 1.0  # Category weight for overall score
    checks: list[AuditCheck] = []


class LighthouseAnalysis(BaseModel):
    url: str = ""
    overall_score: int = 0
    categories: list[LighthouseCategory] = []
    critical_issues: list[str] = []
    warnings: list[str] = []
    passed_checks: list[str] = []


# ── Continuous scoring helpers ────────────────────────────────


def _ratio_score(value: float, target: float) -> float:
    """Score based on how close a ratio is to a target (0.0-1.0)."""
    return min(value / target, 1.0) if target > 0 else 1.0


def _range_score(
    value: float,
    ideal_min: float,
    ideal_max: float,
    abs_min: float = 0,
    abs_max: float = 200,
) -> float:
    """Score based on whether value falls in an ideal range."""
    if ideal_min <= value <= ideal_max:
        return 1.0
    elif value < ideal_min:
        if abs_min >= ideal_min:
            return 0.0
        return max(0.0, (value - abs_min) / (ideal_min - abs_min))
    else:
        if abs_max <= ideal_max:
            return 0.0
        return max(0.0, 1.0 - (value - ideal_max) / (abs_max - ideal_max))


# ── Category scorers ─────────────────────────────────────────


def _score_meta(meta: MetaAnalysis) -> LighthouseCategory:
    """Score meta tags with weighted continuous scoring."""
    cat = LighthouseCategory(category="Meta Tags", weight=2.0)
    checks: list[AuditCheck] = []

    # Title (high weight)
    has_title = meta.title is not None
    checks.append(
        AuditCheck(
            name="Has title tag",
            passed=has_title,
            weight=3.0,
            score=1.0 if has_title else 0.0,
            detail=f"Title: {meta.title}" if has_title else "Missing <title> tag",
        )
    )

    if meta.title:
        title_score = _range_score(meta.title_length, 30, 60, 0, 100)
        checks.append(
            AuditCheck(
                name="Title length",
                passed=title_score >= 0.8,
                weight=2.0,
                score=title_score,
                detail=f"{meta.title_length} chars (~{meta.title_pixel_width}px)",
            )
        )

    # Description (high weight)
    has_desc = meta.description is not None
    checks.append(
        AuditCheck(
            name="Has meta description",
            passed=has_desc,
            weight=3.0,
            score=1.0 if has_desc else 0.0,
            detail=f"Description: {meta.description[:80]}..."
            if has_desc and meta.description
            else "Missing meta description",
        )
    )

    if meta.description:
        desc_score = _range_score(meta.description_length, 70, 160, 0, 250)
        checks.append(
            AuditCheck(
                name="Description length",
                passed=desc_score >= 0.8,
                weight=1.5,
                score=desc_score,
                detail=f"{meta.description_length} chars",
            )
        )

    # Canonical
    has_canonical = meta.canonical is not None
    checks.append(
        AuditCheck(
            name="Has canonical URL",
            passed=has_canonical,
            weight=2.0,
            score=1.0 if has_canonical else 0.0,
            detail=meta.canonical or "Missing canonical",
        )
    )

    # Viewport (critical for mobile)
    has_viewport = meta.viewport is not None
    checks.append(
        AuditCheck(
            name="Has viewport meta",
            passed=has_viewport,
            weight=3.0,
            score=1.0 if has_viewport else 0.0,
            detail="Present" if has_viewport else "Missing — critical for mobile",
        )
    )

    # Other meta
    checks.append(
        AuditCheck(
            name="Has charset",
            passed=meta.charset is not None,
            weight=1.0,
            score=1.0 if meta.charset else 0.0,
        )
    )
    checks.append(
        AuditCheck(
            name="Has lang attribute",
            passed=meta.language is not None,
            weight=1.5,
            score=1.0 if meta.language else 0.0,
        )
    )
    checks.append(
        AuditCheck(
            name="Has Open Graph tags",
            passed=bool(meta.og_tags),
            weight=1.0,
            score=1.0 if meta.og_tags else 0.0,
        )
    )
    checks.append(
        AuditCheck(
            name="Has favicon",
            passed=meta.favicon is not None,
            weight=0.5,
            score=1.0 if meta.favicon else 0.0,
        )
    )

    # Robots check (penalty if noindex)
    if meta.robots and "noindex" in meta.robots.lower():
        checks.append(
            AuditCheck(
                name="Not set to noindex",
                passed=False,
                weight=5.0,
                score=0.0,
                detail="Page is noindex — will not appear in search results",
            )
        )

    cat.checks = checks
    cat.score = _calculate_category_score(checks)
    return cat


def _score_headings(headings: HeadingsAnalysis) -> LighthouseCategory:
    """Score heading structure."""
    cat = LighthouseCategory(category="Heading Structure", weight=1.5)
    checks: list[AuditCheck] = []

    # Single H1
    h1_ok = headings.h1_count == 1
    checks.append(
        AuditCheck(
            name="Single H1 tag",
            passed=h1_ok,
            weight=3.0,
            score=1.0 if h1_ok else (0.5 if headings.h1_count > 1 else 0.0),
            detail=f"H1 count: {headings.h1_count}",
        )
    )

    # Valid hierarchy
    checks.append(
        AuditCheck(
            name="Valid hierarchy",
            passed=headings.hierarchy_valid,
            weight=2.0,
            score=1.0 if headings.hierarchy_valid else 0.3,
        )
    )

    # Sufficient headings
    sufficient = headings.total_count >= 3
    heading_score = min(headings.total_count / 3, 1.0) if headings.total_count < 3 else 1.0
    checks.append(
        AuditCheck(
            name="Sufficient headings",
            passed=sufficient,
            weight=1.0,
            score=heading_score,
            detail=f"{headings.total_count} headings",
        )
    )

    # No duplicates
    has_dupes = bool(headings.duplicate_headings)
    checks.append(
        AuditCheck(
            name="No duplicate headings",
            passed=not has_dupes,
            weight=1.0,
            score=0.5 if has_dupes else 1.0,
            detail=f"{len(headings.duplicate_headings)} duplicates" if has_dupes else "No duplicates",
        )
    )

    cat.checks = checks
    cat.score = _calculate_category_score(checks)
    return cat


def _score_content(content: ContentAnalysis) -> LighthouseCategory:
    """Score content quality."""
    cat = LighthouseCategory(category="Content Quality", weight=2.0)
    checks: list[AuditCheck] = []

    # Word count (continuous)
    wc_score = min(content.word_count / 300, 1.0)
    checks.append(
        AuditCheck(
            name="Content length",
            passed=content.word_count >= 300,
            weight=2.0,
            score=wc_score,
            detail=f"{content.word_count} words",
        )
    )

    # Text/HTML ratio (continuous)
    ratio_score = min(content.text_to_html_ratio / 10, 1.0)
    checks.append(
        AuditCheck(
            name="Text/HTML ratio",
            passed=content.text_to_html_ratio >= 10,
            weight=1.5,
            score=ratio_score,
            detail=f"{content.text_to_html_ratio}%",
        )
    )

    # Readability
    readability_score = min(max(content.flesch_reading_ease, 0) / 60, 1.0)
    checks.append(
        AuditCheck(
            name="Readability",
            passed=content.flesch_reading_ease >= 50,
            weight=1.5,
            score=readability_score,
            detail=f"Flesch: {content.flesch_reading_ease} ({content.readability_level})",
        )
    )

    # Sentence length
    sent_ok = content.avg_sentence_length <= 25
    checks.append(
        AuditCheck(
            name="Sentence length",
            passed=sent_ok,
            weight=1.0,
            score=1.0 if sent_ok else max(0, 1.0 - (content.avg_sentence_length - 25) / 15),
            detail=f"Avg {content.avg_sentence_length} words/sentence",
        )
    )

    # Paragraphs
    para_score = min(content.paragraph_count / 3, 1.0)
    checks.append(
        AuditCheck(
            name="Multiple paragraphs",
            passed=content.paragraph_count >= 3,
            weight=0.5,
            score=para_score,
        )
    )

    cat.checks = checks
    cat.score = _calculate_category_score(checks)
    return cat


def _score_images(images: ImagesAnalysis) -> LighthouseCategory:
    """Score image optimization."""
    cat = LighthouseCategory(category="Images", weight=1.0)

    if images.total_images == 0:
        cat.score = 100
        cat.checks.append(AuditCheck(name="No images to audit", passed=True, score=1.0))
        return cat

    checks: list[AuditCheck] = []

    # Alt text coverage (continuous)
    alt_ratio = images.images_with_alt / images.total_images if images.total_images else 1
    checks.append(
        AuditCheck(
            name="Alt text coverage",
            passed=alt_ratio >= 0.9,
            weight=3.0,
            score=alt_ratio,
            detail=f"{images.images_with_alt}/{images.total_images} images have alt text",
        )
    )

    # Lazy loading
    lazy_ratio = images.images_lazy_loaded / images.total_images if images.total_images else 1
    checks.append(
        AuditCheck(
            name="Lazy loading",
            passed=lazy_ratio >= 0.5,
            weight=1.5,
            score=min(lazy_ratio / 0.5, 1.0),
            detail=f"{images.images_lazy_loaded}/{images.total_images} lazy loaded",
        )
    )

    # Dimensions
    dim_ratio = images.images_with_dimensions / images.total_images if images.total_images else 1
    checks.append(
        AuditCheck(
            name="Explicit dimensions",
            passed=dim_ratio >= 0.7,
            weight=2.0,
            score=dim_ratio,
            detail=f"{images.images_with_dimensions}/{images.total_images} with dimensions",
        )
    )

    # Modern formats
    if images.total_images > 0:
        total_with_format = images.modern_format_count + images.legacy_format_count
        if total_with_format > 0:
            modern_ratio = images.modern_format_count / total_with_format
            checks.append(
                AuditCheck(
                    name="Modern formats",
                    passed=modern_ratio >= 0.7,
                    weight=1.5,
                    score=modern_ratio,
                    detail=f"{images.modern_format_count}/{total_with_format} using WebP/AVIF/SVG",
                )
            )

    # Srcset usage
    if images.total_images > 3:
        srcset_ratio = images.images_with_srcset / images.total_images
        checks.append(
            AuditCheck(
                name="Responsive images (srcset)",
                passed=srcset_ratio > 0,
                weight=1.0,
                score=min(srcset_ratio / 0.5, 1.0),
                detail=f"{images.images_with_srcset}/{images.total_images} use srcset",
            )
        )

    cat.checks = checks
    cat.score = _calculate_category_score(checks)
    return cat


def _score_structured_data(sd: StructuredDataAnalysis) -> LighthouseCategory:
    """Score structured data."""
    cat = LighthouseCategory(category="Structured Data", weight=1.0)
    checks: list[AuditCheck] = []

    has_sd = sd.total_items > 0
    checks.append(
        AuditCheck(
            name="Has structured data",
            passed=has_sd,
            weight=2.0,
            score=1.0 if has_sd else 0.0,
        )
    )

    if has_sd:
        valid_ratio = sum(1 for i in sd.items if i.valid) / len(sd.items) if sd.items else 1
        checks.append(
            AuditCheck(
                name="All structured data valid",
                passed=valid_ratio == 1.0,
                weight=2.0,
                score=valid_ratio,
            )
        )

        checks.append(
            AuditCheck(
                name="Has WebSite schema",
                passed=sd.has_website_schema,
                weight=1.0,
                score=1.0 if sd.has_website_schema else 0.0,
            )
        )

        checks.append(
            AuditCheck(
                name="Has Organization schema",
                passed=sd.has_organization_schema,
                weight=1.0,
                score=1.0 if sd.has_organization_schema else 0.0,
            )
        )

        has_rich = bool(sd.rich_result_types)
        checks.append(
            AuditCheck(
                name="Rich Result eligible types",
                passed=has_rich,
                weight=1.5,
                score=1.0 if has_rich else 0.3,
                detail=", ".join(sd.rich_result_types) if has_rich else "None",
            )
        )

    cat.checks = checks
    cat.score = _calculate_category_score(checks)
    return cat


def _score_links(links: LinksAnalysis) -> LighthouseCategory:
    """Score link structure."""
    cat = LighthouseCategory(category="Links", weight=1.0)
    checks: list[AuditCheck] = []

    has_internal = bool(links.internal_links)
    checks.append(
        AuditCheck(
            name="Has internal links",
            passed=has_internal,
            weight=2.0,
            score=1.0 if has_internal else 0.0,
        )
    )

    # No links without text
    if links.total_links > 0:
        text_ratio = 1 - (len(links.links_without_text) / links.total_links)
        checks.append(
            AuditCheck(
                name="Links have anchor text",
                passed=text_ratio >= 0.95,
                weight=1.5,
                score=text_ratio,
                detail=f"{len(links.links_without_text)} without text",
            )
        )

    # Follow ratio
    if links.total_links > 0:
        checks.append(
            AuditCheck(
                name="Follow ratio",
                passed=links.follow_ratio >= 50,
                weight=1.0,
                score=min(links.follow_ratio / 50, 1.0),
                detail=f"{links.follow_ratio}% followed",
            )
        )

    # No broken links
    no_broken = len(links.broken_links) == 0
    checks.append(
        AuditCheck(
            name="No broken links",
            passed=no_broken,
            weight=2.0,
            score=1.0 if no_broken else max(0, 1.0 - len(links.broken_links) / 10),
            detail=f"{len(links.broken_links)} broken" if not no_broken else "All links OK",
        )
    )

    cat.checks = checks
    cat.score = _calculate_category_score(checks)
    return cat


# ── Score calculation ─────────────────────────────────────────


def _calculate_category_score(checks: list[AuditCheck]) -> int:
    """Calculate weighted score for a category (0-100)."""
    if not checks:
        return 100

    total_weight = sum(c.weight for c in checks)
    if total_weight == 0:
        return 100

    weighted_sum = sum(c.score * c.weight for c in checks)
    return round((weighted_sum / total_weight) * 100)


# ── Main runner ───────────────────────────────────────────────


def run_lighthouse(html: str, url: str = "") -> LighthouseAnalysis:
    """Run a lighthouse-style audit on HTML content."""
    meta = analyze_meta(html, url)
    headings = analyze_headings(html)
    links = analyze_links(html, url)
    images = analyze_images(html, url)
    sd = analyze_structured_data(html)
    content = analyze_content(html)

    categories = [
        _score_meta(meta),
        _score_headings(headings),
        _score_content(content),
        _score_images(images),
        _score_structured_data(sd),
        _score_links(links),
    ]

    # Weighted overall score
    total_weight = sum(c.weight for c in categories)
    overall = round(sum(c.score * c.weight for c in categories) / total_weight) if total_weight > 0 else 0

    # Categorize issues by severity
    critical_issues: list[str] = []
    warnings: list[str] = []
    passed_checks: list[str] = []

    all_issues = meta.issues + headings.issues + links.issues + images.issues + sd.issues + content.issues

    for issue in all_issues:
        if "CRITICAL" in issue:
            critical_issues.append(issue)
        else:
            warnings.append(issue)

    for cat in categories:
        for check in cat.checks:
            if check.passed:
                passed_checks.append(f"[{cat.category}] {check.name}")

    return LighthouseAnalysis(
        url=url,
        overall_score=overall,
        categories=categories,
        critical_issues=critical_issues,
        warnings=warnings,
        passed_checks=passed_checks,
    )


# ── Report formatter ──────────────────────────────────────────


def format_lighthouse_report(analysis: LighthouseAnalysis) -> str:
    """Format lighthouse analysis as a readable report."""
    lines = ["# SEO Audit Report", ""]

    # Overall score with visual indicator
    score = analysis.overall_score
    if score >= 90:
        indicator = "EXCELLENT"
    elif score >= 70:
        indicator = "GOOD"
    elif score >= 50:
        indicator = "NEEDS IMPROVEMENT"
    else:
        indicator = "POOR"

    lines.append(f"## Overall Score: {score}/100 ({indicator})")
    lines.append("")

    # Category breakdown
    lines.append("## Category Scores")
    lines.append("")
    for cat in analysis.categories:
        if cat.score >= 90:
            status = "GOOD"
        elif cat.score >= 50:
            status = "OK"
        else:
            status = "POOR"

        lines.append(f"### {cat.category}: {cat.score}/100 [{status}]")
        for check in cat.checks:
            icon = "PASS" if check.passed else "FAIL"
            score_pct = int(check.score * 100)
            detail = f" — {check.detail}" if check.detail else ""
            lines.append(f"  - [{icon}] {check.name} ({score_pct}%){detail}")
        lines.append("")

    # Critical issues first
    if analysis.critical_issues:
        lines.append("## Critical Issues")
        for i, issue in enumerate(analysis.critical_issues, 1):
            lines.append(f"{i}. {issue}")
        lines.append("")

    if analysis.warnings:
        lines.append("## Warnings")
        for i, issue in enumerate(analysis.warnings, 1):
            lines.append(f"{i}. {issue}")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append(f"- **Passed checks**: {len(analysis.passed_checks)}")
    lines.append(f"- **Critical issues**: {len(analysis.critical_issues)}")
    lines.append(f"- **Warnings**: {len(analysis.warnings)}")
    lines.append("")

    return "\n".join(lines)
