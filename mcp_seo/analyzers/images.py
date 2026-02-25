"""Image analysis: alt text, dimensions, format, lazy loading."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import BaseModel


class ImageItem(BaseModel):
    src: str
    alt: str | None = None
    has_alt: bool = False
    width: str | None = None
    height: str | None = None
    loading: str | None = None
    is_lazy: bool = False
    is_decorative: bool = False
    format: str | None = None


class ImagesAnalysis(BaseModel):
    total_images: int = 0
    images_with_alt: int = 0
    images_without_alt: int = 0
    images_lazy_loaded: int = 0
    images_with_dimensions: int = 0
    images: list[ImageItem] = []
    issues: list[str] = []


def _detect_format(src: str) -> str | None:
    """Detect image format from URL."""
    src_lower = src.lower().split("?")[0]
    for ext in (".webp", ".avif", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico"):
        if src_lower.endswith(ext):
            return ext.lstrip(".")
    return None


def analyze_images(html: str, base_url: str = "") -> ImagesAnalysis:
    """Analyze all images on a page."""
    soup = BeautifulSoup(html, "lxml")
    result = ImagesAnalysis()
    issues: list[str] = []
    images: list[ImageItem] = []

    for img in soup.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "") or ""
        if base_url and src:
            src = urljoin(base_url, src)

        alt = img.get("alt")
        has_alt = alt is not None
        loading = img.get("loading")
        width = img.get("width")
        height = img.get("height")

        item = ImageItem(
            src=src,
            alt=alt,
            has_alt=has_alt,
            width=width,
            height=height,
            loading=loading,
            is_lazy=loading == "lazy",
            is_decorative=alt == "",
            format=_detect_format(src),
        )
        images.append(item)

    result.images = images
    result.total_images = len(images)
    result.images_with_alt = sum(1 for i in images if i.has_alt and not i.is_decorative)
    result.images_without_alt = sum(1 for i in images if not i.has_alt)
    result.images_lazy_loaded = sum(1 for i in images if i.is_lazy)
    result.images_with_dimensions = sum(1 for i in images if i.width and i.height)

    # Issues
    if result.images_without_alt > 0:
        issues.append(f"{result.images_without_alt} images missing alt text")

    non_lazy_count = result.total_images - result.images_lazy_loaded
    if non_lazy_count > 3:  # Allow a few above-the-fold images
        issues.append(f"{non_lazy_count} images without lazy loading")

    without_dims = result.total_images - result.images_with_dimensions
    if without_dims > 0:
        issues.append(f"{without_dims} images without explicit width/height (causes CLS)")

    # Check for modern formats
    non_modern = [i for i in images if i.format and i.format not in ("webp", "avif", "svg")]
    if non_modern:
        issues.append(f"{len(non_modern)} images not using modern formats (WebP/AVIF)")

    result.issues = issues
    return result


def format_images_report(analysis: ImagesAnalysis) -> str:
    """Format image analysis as a readable report."""
    lines = ["# Image Analysis", ""]

    lines.append(f"**Total images**: {analysis.total_images}")
    lines.append(f"**With alt text**: {analysis.images_with_alt}")
    lines.append(f"**Without alt text**: {analysis.images_without_alt}")
    lines.append(f"**Lazy loaded**: {analysis.images_lazy_loaded}")
    lines.append(f"**With dimensions**: {analysis.images_with_dimensions}")
    lines.append("")

    if analysis.images:
        lines.append("## Image Details (first 20)")
        for img in analysis.images[:20]:
            alt_status = "✅" if img.has_alt else "❌"
            lazy_status = "lazy" if img.is_lazy else "eager"
            fmt = img.format or "unknown"
            lines.append(f"- {alt_status} `{img.src[:80]}` | alt={img.alt!r} | {fmt} | {lazy_status}")
        if len(analysis.images) > 20:
            lines.append(f"- ... and {len(analysis.images) - 20} more")
        lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
