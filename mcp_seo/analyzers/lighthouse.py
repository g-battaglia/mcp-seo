"""Lighthouse-style comprehensive SEO audit."""

from __future__ import annotations

from pydantic import BaseModel

from mcp_seo.analyzers.meta import MetaAnalysis, analyze_meta
from mcp_seo.analyzers.headings import HeadingsAnalysis, analyze_headings
from mcp_seo.analyzers.links import LinksAnalysis, analyze_links
from mcp_seo.analyzers.images import ImagesAnalysis, analyze_images
from mcp_seo.analyzers.structured_data import (
    StructuredDataAnalysis,
    analyze_structured_data,
)
from mcp_seo.analyzers.content import ContentAnalysis, analyze_content


class LighthouseScore(BaseModel):
    category: str
    score: int = 0  # 0-100
    passed: list[str] = []
    failed: list[str] = []


class LighthouseAnalysis(BaseModel):
    url: str = ""
    overall_score: int = 0
    categories: list[LighthouseScore] = []
    all_issues: list[str] = []


def _score_meta(meta: MetaAnalysis) -> LighthouseScore:
    """Score meta tags (0-100)."""
    score = LighthouseScore(category="Meta Tags")
    total = 10
    passed = 0

    checks = [
        (meta.title is not None, "Has title tag", "Missing title tag"),
        (
            meta.title_length >= 30 if meta.title else False,
            "Title length OK",
            "Title too short/missing",
        ),
        (
            meta.title_length <= 60 if meta.title else False,
            "Title not too long",
            "Title too long",
        ),
        (
            meta.description is not None,
            "Has meta description",
            "Missing meta description",
        ),
        (
            meta.description_length >= 70 if meta.description else False,
            "Description length OK",
            "Description too short",
        ),
        (meta.canonical is not None, "Has canonical URL", "Missing canonical"),
        (meta.viewport is not None, "Has viewport meta", "Missing viewport"),
        (meta.charset is not None, "Has charset", "Missing charset"),
        (meta.language is not None, "Has lang attribute", "Missing lang"),
        (bool(meta.og_tags), "Has Open Graph tags", "Missing OG tags"),
    ]

    for passed_check, pass_msg, fail_msg in checks:
        if passed_check:
            score.passed.append(pass_msg)
            passed += 1
        else:
            score.failed.append(fail_msg)

    score.score = int((passed / total) * 100)
    return score


def _score_headings(headings: HeadingsAnalysis) -> LighthouseScore:
    """Score heading structure (0-100)."""
    score = LighthouseScore(category="Heading Structure")
    total = 4
    passed = 0

    checks = [
        (headings.h1_count == 1, "Single H1 tag", f"H1 count: {headings.h1_count}"),
        (headings.hierarchy_valid, "Valid hierarchy", "Invalid heading hierarchy"),
        (headings.total_count >= 3, "Sufficient headings", "Too few headings"),
        (
            headings.total_count <= 30,
            "Not too many headings",
            f"Too many headings ({headings.total_count})",
        ),
    ]

    for passed_check, pass_msg, fail_msg in checks:
        if passed_check:
            score.passed.append(pass_msg)
            passed += 1
        else:
            score.failed.append(fail_msg)

    score.score = int((passed / total) * 100)
    return score


def _score_content(content: ContentAnalysis) -> LighthouseScore:
    """Score content quality (0-100)."""
    score = LighthouseScore(category="Content Quality")
    total = 4
    passed = 0

    checks = [
        (
            content.word_count >= 300,
            "Sufficient content length",
            f"Thin content ({content.word_count} words)",
        ),
        (
            content.text_to_html_ratio >= 10,
            "Good text/HTML ratio",
            f"Low text/HTML ratio ({content.text_to_html_ratio}%)",
        ),
        (content.avg_sentence_length <= 25, "Readable sentences", "Long sentences"),
        (content.paragraph_count >= 3, "Multiple paragraphs", "Too few paragraphs"),
    ]

    for passed_check, pass_msg, fail_msg in checks:
        if passed_check:
            score.passed.append(pass_msg)
            passed += 1
        else:
            score.failed.append(fail_msg)

    score.score = int((passed / total) * 100)
    return score


def _score_images(images: ImagesAnalysis) -> LighthouseScore:
    """Score image optimization (0-100)."""
    score = LighthouseScore(category="Images")

    if images.total_images == 0:
        score.score = 100
        score.passed.append("No images to audit")
        return score

    total = 3
    passed = 0

    alt_ratio = (
        images.images_with_alt / images.total_images if images.total_images else 1
    )
    lazy_ratio = (
        images.images_lazy_loaded / images.total_images if images.total_images else 1
    )
    dim_ratio = (
        images.images_with_dimensions / images.total_images
        if images.total_images
        else 1
    )

    checks = [
        (
            alt_ratio >= 0.9,
            "Good alt text coverage",
            f"Missing alt text on {images.images_without_alt} images",
        ),
        (lazy_ratio >= 0.5, "Lazy loading used", "Insufficient lazy loading"),
        (dim_ratio >= 0.7, "Explicit dimensions set", "Missing image dimensions"),
    ]

    for passed_check, pass_msg, fail_msg in checks:
        if passed_check:
            score.passed.append(pass_msg)
            passed += 1
        else:
            score.failed.append(fail_msg)

    score.score = int((passed / total) * 100)
    return score


def _score_structured_data(sd: StructuredDataAnalysis) -> LighthouseScore:
    """Score structured data (0-100)."""
    score = LighthouseScore(category="Structured Data")
    total = 2
    passed = 0

    checks = [
        (sd.total_items > 0, "Has structured data", "No structured data found"),
        (
            all(i.valid for i in sd.items),
            "All structured data valid",
            "Invalid structured data found",
        ),
    ]

    for passed_check, pass_msg, fail_msg in checks:
        if passed_check:
            score.passed.append(pass_msg)
            passed += 1
        else:
            score.failed.append(fail_msg)

    score.score = int((passed / total) * 100)
    return score


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
    ]

    all_issues = (
        meta.issues
        + headings.issues
        + links.issues
        + images.issues
        + sd.issues
        + content.issues
    )

    overall = (
        int(sum(c.score for c in categories) / len(categories)) if categories else 0
    )

    return LighthouseAnalysis(
        url=url,
        overall_score=overall,
        categories=categories,
        all_issues=all_issues,
    )


def format_lighthouse_report(analysis: LighthouseAnalysis) -> str:
    """Format lighthouse analysis as a readable report."""
    lines = ["# 🔦 Lighthouse-Style SEO Audit", ""]

    # Overall score with visual indicator
    score = analysis.overall_score
    if score >= 90:
        indicator = "🟢"
    elif score >= 50:
        indicator = "🟡"
    else:
        indicator = "🔴"

    lines.append(f"## Overall Score: {indicator} {score}/100")
    lines.append("")

    for cat in analysis.categories:
        if cat.score >= 90:
            ind = "🟢"
        elif cat.score >= 50:
            ind = "🟡"
        else:
            ind = "🔴"

        lines.append(f"### {ind} {cat.category}: {cat.score}/100")
        if cat.passed:
            for p in cat.passed:
                lines.append(f"  - ✅ {p}")
        if cat.failed:
            for f in cat.failed:
                lines.append(f"  - ❌ {f}")
        lines.append("")

    if analysis.all_issues:
        lines.append("## All Issues (Prioritized)")
        for i, issue in enumerate(analysis.all_issues, 1):
            lines.append(f"{i}. {issue}")
        lines.append("")

    return "\n".join(lines)
