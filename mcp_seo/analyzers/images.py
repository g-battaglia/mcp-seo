"""Image analysis: alt text, dimensions, format, lazy loading, srcset, picture element."""

from __future__ import annotations

from urllib.parse import urljoin

from pydantic import BaseModel

from mcp_seo.utils import get_logger, parse_html

logger = get_logger("images")


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
    has_srcset: bool = False
    in_picture: bool = False


class ImagesAnalysis(BaseModel):
    total_images: int = 0
    images_with_alt: int = 0
    images_without_alt: int = 0
    images_lazy_loaded: int = 0
    images_with_dimensions: int = 0
    images_with_srcset: int = 0
    images_in_picture: int = 0
    images: list[ImageItem] = []

    # Format breakdown
    format_counts: dict[str, int] = {}
    modern_format_count: int = 0
    legacy_format_count: int = 0

    issues: list[str] = []


def _detect_format(src: str) -> str | None:
    """Detect image format from URL."""
    src_lower = src.lower().split("?")[0].split("#")[0]
    for ext in (
        ".webp",
        ".avif",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".tiff",
    ):
        if src_lower.endswith(ext):
            return ext.lstrip(".")
    return None


_MODERN_FORMATS = {"webp", "avif", "svg"}


def analyze_images(html: str, base_url: str = "") -> ImagesAnalysis:
    """Analyze all images on a page."""
    soup = parse_html(html)
    result = ImagesAnalysis()
    issues: list[str] = []
    images: list[ImageItem] = []
    format_counts: dict[str, int] = {}

    # Track picture elements and their <source> types
    picture_imgs = set()
    picture_has_modern_source: dict[int, bool] = {}  # img id -> has modern source
    for picture in soup.find_all("picture"):
        # Check if any <source> provides modern formats
        has_modern = False
        for source in picture.find_all("source"):
            source_type = str(source.get("type", "")).lower()
            source_srcset = str(source.get("srcset", "")).lower()
            if any(fmt in source_type for fmt in ("webp", "avif")) or any(
                fmt in source_srcset for fmt in (".webp", ".avif")
            ):
                has_modern = True
                break
        for img in picture.find_all("img"):
            picture_imgs.add(id(img))
            picture_has_modern_source[id(img)] = has_modern

    for img in soup.find_all("img"):
        src = str(img.get("src", "") or img.get("data-src", "") or "")
        if base_url and src:
            src = urljoin(base_url, src)

        alt = img.get("alt")
        alt_str = str(alt) if alt is not None else None
        has_alt = alt is not None
        loading = str(img.get("loading", "")) or None
        width = str(img.get("width", "")) or None
        height = str(img.get("height", "")) or None
        has_srcset = bool(img.get("srcset"))
        in_picture = id(img) in picture_imgs

        fmt = _detect_format(src)

        item = ImageItem(
            src=src,
            alt=alt_str,
            has_alt=has_alt,
            width=width if width else None,
            height=height if height else None,
            loading=loading if loading else None,
            is_lazy=loading == "lazy",
            is_decorative=alt_str == "",
            format=fmt,
            has_srcset=has_srcset,
            in_picture=in_picture,
        )
        images.append(item)

        if fmt:
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

    result.images = images
    result.total_images = len(images)
    result.images_with_alt = sum(1 for i in images if i.has_alt and not i.is_decorative)
    result.images_without_alt = sum(1 for i in images if not i.has_alt)
    result.images_lazy_loaded = sum(1 for i in images if i.is_lazy)
    result.images_with_dimensions = sum(1 for i in images if i.width and i.height)
    result.images_with_srcset = sum(1 for i in images if i.has_srcset)
    result.images_in_picture = sum(1 for i in images if i.in_picture)
    result.format_counts = format_counts
    result.modern_format_count = sum(count for fmt, count in format_counts.items() if fmt in _MODERN_FORMATS)
    result.legacy_format_count = sum(count for fmt, count in format_counts.items() if fmt not in _MODERN_FORMATS)

    # Issues
    if result.images_without_alt > 0:
        issues.append(f"{result.images_without_alt} images missing alt text")

    non_lazy_count = result.total_images - result.images_lazy_loaded
    if non_lazy_count > 3:  # Allow a few above-the-fold images
        issues.append(f"{non_lazy_count} images without lazy loading")

    without_dims = result.total_images - result.images_with_dimensions
    if without_dims > 0:
        issues.append(f"{without_dims} images without explicit width/height (causes CLS)")

    # Check for modern formats — exclude images served via <picture> with modern <source>
    if result.legacy_format_count > 0:
        # Count truly legacy images (not those wrapped in <picture> with modern sources)
        truly_legacy = 0
        for img_item in images:
            if img_item.format and img_item.format not in _MODERN_FORMATS:
                if img_item.in_picture:
                    # Check if the <picture> has a modern <source>
                    # If yes, the browser will serve the modern format
                    img_tag = next(
                        (
                            t
                            for t in soup.find_all("img")
                            if id(t) in picture_has_modern_source
                            and picture_has_modern_source[id(t)]
                            and str(t.get("src", "")) in img_item.src
                        ),
                        None,
                    )
                    if img_tag is None:
                        truly_legacy += 1
                else:
                    truly_legacy += 1
        if truly_legacy > 0:
            issues.append(
                f"{truly_legacy} images not using modern formats (WebP/AVIF). "
                f"Consider converting for ~25-50% size reduction."
            )

    # srcset usage
    if result.total_images > 3 and result.images_with_srcset == 0:
        issues.append("No images use srcset — responsive images not implemented")

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
    lines.append(f"**With srcset**: {analysis.images_with_srcset}")
    lines.append(f"**In <picture>**: {analysis.images_in_picture}")
    lines.append("")

    if analysis.format_counts:
        lines.append("## Format Breakdown")
        for fmt, count in sorted(analysis.format_counts.items(), key=lambda x: -x[1]):
            modern = " (modern)" if fmt in _MODERN_FORMATS else " (legacy)"
            lines.append(f"- **{fmt}**: {count}{modern}")
        lines.append("")

    if analysis.images:
        lines.append("## Image Details (first 25)")
        for img in analysis.images[:25]:
            alt_status = "ok" if img.has_alt else "MISSING"
            lazy_status = "lazy" if img.is_lazy else "eager"
            fmt = img.format or "unknown"
            srcset = " +srcset" if img.has_srcset else ""
            picture = " +picture" if img.in_picture else ""
            lines.append(
                f"- [{alt_status}] `{img.src[:80]}` | alt={img.alt!r} | {fmt} | {lazy_status}{srcset}{picture}"
            )
        if len(analysis.images) > 25:
            lines.append(f"- ... and {len(analysis.images) - 25} more")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
