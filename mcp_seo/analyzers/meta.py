"""Meta tags analysis: title, description, OG, Twitter Cards, canonical, hreflang, favicon."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import BaseModel

from mcp_seo.config import Config
from mcp_seo.utils import get_logger, parse_html

logger = get_logger("meta")

# ── Pixel-width estimation ────────────────────────────────────
# Average character widths in pixels at ~16px font (Arial/Helvetica).
# Google SERP uses ~600px for title, ~920px for description on desktop.
_CHAR_WIDTH_NARROW = 5.5  # i, l, t, r, f, j, 1
_CHAR_WIDTH_WIDE = 9.0  # m, w, M, W
_CHAR_WIDTH_AVG = 7.0  # average character

_NARROW_CHARS = set("iltrf j1!|.,:;'")
_WIDE_CHARS = set("mwMWGOQD@%")

TITLE_MAX_PX = Config.title_max_px()
DESC_MAX_PX = Config.desc_max_px()


def _estimate_pixel_width(text: str) -> float:
    """Estimate the pixel width of text in Google SERP."""
    width = 0.0
    for ch in text:
        if ch in _NARROW_CHARS:
            width += _CHAR_WIDTH_NARROW
        elif ch in _WIDE_CHARS:
            width += _CHAR_WIDTH_WIDE
        elif ch == " ":
            width += 4.0
        elif ch.isupper():
            width += 8.5
        else:
            width += _CHAR_WIDTH_AVG
    return round(width, 1)


# ── Models ────────────────────────────────────────────────────


class HreflangEntry(BaseModel):
    lang: str
    url: str
    is_valid_lang: bool = True


class MetaAnalysis(BaseModel):
    """Result of meta tags analysis."""

    title: str | None = None
    title_length: int = 0
    title_pixel_width: float = 0.0
    description: str | None = None
    description_length: int = 0
    description_pixel_width: float = 0.0
    canonical: str | None = None
    canonical_is_self: bool = False
    robots: str | None = None
    robots_directives: dict[str, str] = {}  # max-snippet, max-image-preview, etc.
    viewport: str | None = None
    charset: str | None = None
    language: str | None = None

    # Hreflang
    hreflang_tags: list[HreflangEntry] = []

    # Favicon
    favicon: str | None = None

    og_tags: dict[str, str] = {}
    twitter_tags: dict[str, str] = {}
    other_meta: dict[str, str] = {}
    issues: list[str] = []


# ── Analyzer ──────────────────────────────────────────────────


def analyze_meta(html: str, url: str = "") -> MetaAnalysis:
    """Analyze meta tags from HTML content."""
    soup = parse_html(html)
    result = MetaAnalysis()
    issues: list[str] = []

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        result.title = title_tag.string.strip()
        result.title_length = len(result.title)
        result.title_pixel_width = _estimate_pixel_width(result.title)

        if result.title_length < 30:
            issues.append(f"Title too short ({result.title_length} chars, recommended 30-60)")
        elif result.title_length > 60:
            issues.append(f"Title too long ({result.title_length} chars, recommended 30-60)")

        if result.title_pixel_width > TITLE_MAX_PX:
            issues.append(
                f"Title may be truncated in SERP (~{result.title_pixel_width}px, Google limit ~{TITLE_MAX_PX}px)"
            )
    else:
        issues.append("CRITICAL: Missing <title> tag. Add a unique, descriptive <title> in the <head> section.")

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        result.description = str(desc["content"]).strip()
        result.description_length = len(result.description)
        result.description_pixel_width = _estimate_pixel_width(result.description)

        if result.description_length < 70:
            issues.append(f"Meta description too short ({result.description_length} chars, recommended 70-160)")
        elif result.description_length > 160:
            issues.append(f"Meta description too long ({result.description_length} chars, recommended 70-160)")

        if result.description_pixel_width > DESC_MAX_PX:
            issues.append(f"Description may be truncated in SERP (~{result.description_pixel_width}px)")
    else:
        issues.append(
            'CRITICAL: Missing meta description. Add <meta name="description" content="..."> with 70-160 chars.'
        )

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        result.canonical = str(canonical["href"])
        # Check if canonical is self-referencing
        if url:
            parsed_canonical = urlparse(result.canonical)
            parsed_url = urlparse(url)
            result.canonical_is_self = parsed_canonical.netloc == parsed_url.netloc and parsed_canonical.path.rstrip(
                "/"
            ) == parsed_url.path.rstrip("/")
            if not result.canonical_is_self:
                issues.append(f"Canonical points to different URL: {result.canonical} (may be intentional)")
    else:
        issues.append('Missing canonical URL. Add <link rel="canonical" href="..."> to prevent duplicate content.')

    # Robots
    robots = soup.find("meta", attrs={"name": "robots"})
    if robots and robots.get("content"):
        result.robots = str(robots["content"])
        robots_lower = result.robots.lower()
        if "noindex" in robots_lower:
            issues.append("CRITICAL: Page is set to noindex")
        if "nofollow" in robots_lower:
            issues.append("Page is set to nofollow — links won't pass equity")

        # Parse advanced directives (max-snippet, max-image-preview, max-video-preview)
        for directive in result.robots.split(","):
            directive = directive.strip()
            if ":" in directive:
                key, _, value = directive.partition(":")
                result.robots_directives[key.strip().lower()] = value.strip()

        if "max-snippet" in result.robots_directives:
            val = result.robots_directives["max-snippet"]
            if val == "0":
                issues.append("max-snippet:0 prevents text snippets in SERP — this significantly reduces CTR")
        if "max-image-preview" in result.robots_directives:
            val = result.robots_directives["max-image-preview"]
            if val == "none":
                issues.append("max-image-preview:none prevents image thumbnails in SERP")

    # Viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport and viewport.get("content"):
        result.viewport = str(viewport["content"])
    else:
        issues.append(
            'CRITICAL: Missing viewport meta tag (mobile-friendliness issue). Add <meta name="viewport" content="width=device-width, initial-scale=1.0">.'
        )

    # Charset
    charset = soup.find("meta", attrs={"charset": True})
    if charset:
        result.charset = str(charset.get("charset", ""))
    else:
        charset_http = soup.find("meta", attrs={"http-equiv": "Content-Type"})
        if charset_http:
            result.charset = str(charset_http.get("content", ""))
        else:
            issues.append('Missing charset declaration. Add <meta charset="UTF-8"> as the first tag in <head>.')

    # Language
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        result.language = str(html_tag["lang"])
    else:
        issues.append('Missing lang attribute on <html> tag. Add lang="en" (or appropriate language code) to <html>.')

    # Hreflang
    # ISO 639-1 language codes (2-letter) — most common subset
    _VALID_LANG_CODES = {
        "aa",
        "ab",
        "af",
        "ak",
        "am",
        "an",
        "ar",
        "as",
        "av",
        "ay",
        "az",
        "ba",
        "be",
        "bg",
        "bh",
        "bi",
        "bm",
        "bn",
        "bo",
        "br",
        "bs",
        "ca",
        "ce",
        "ch",
        "co",
        "cr",
        "cs",
        "cu",
        "cv",
        "cy",
        "da",
        "de",
        "dv",
        "dz",
        "ee",
        "el",
        "en",
        "eo",
        "es",
        "et",
        "eu",
        "fa",
        "ff",
        "fi",
        "fj",
        "fo",
        "fr",
        "fy",
        "ga",
        "gd",
        "gl",
        "gn",
        "gu",
        "gv",
        "ha",
        "he",
        "hi",
        "ho",
        "hr",
        "ht",
        "hu",
        "hy",
        "hz",
        "ia",
        "id",
        "ie",
        "ig",
        "ii",
        "ik",
        "in",
        "io",
        "is",
        "it",
        "iu",
        "ja",
        "jv",
        "ka",
        "kg",
        "ki",
        "kj",
        "kk",
        "kl",
        "km",
        "kn",
        "ko",
        "kr",
        "ks",
        "ku",
        "kv",
        "kw",
        "ky",
        "la",
        "lb",
        "lg",
        "li",
        "ln",
        "lo",
        "lt",
        "lu",
        "lv",
        "mg",
        "mh",
        "mi",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "mt",
        "my",
        "na",
        "nb",
        "nd",
        "ne",
        "ng",
        "nl",
        "nn",
        "no",
        "nr",
        "nv",
        "ny",
        "oc",
        "oj",
        "om",
        "or",
        "os",
        "pa",
        "pi",
        "pl",
        "ps",
        "pt",
        "qu",
        "rm",
        "rn",
        "ro",
        "ru",
        "rw",
        "sa",
        "sc",
        "sd",
        "se",
        "sg",
        "si",
        "sk",
        "sl",
        "sm",
        "sn",
        "so",
        "sq",
        "sr",
        "ss",
        "st",
        "su",
        "sv",
        "sw",
        "ta",
        "te",
        "tg",
        "th",
        "ti",
        "tk",
        "tl",
        "tn",
        "to",
        "tr",
        "ts",
        "tt",
        "tw",
        "ty",
        "ug",
        "uk",
        "ur",
        "uz",
        "ve",
        "vi",
        "vo",
        "wa",
        "wo",
        "xh",
        "yi",
        "yo",
        "za",
        "zh",
        "zu",
    }

    for link in soup.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
        href = link.get("href", "")
        hreflang = link.get("hreflang", "")
        if href and hreflang:
            lang_str = str(hreflang)
            # Validate BCP 47 language tag
            is_valid = True
            if lang_str != "x-default":
                # Extract primary language subtag
                primary = lang_str.split("-")[0].lower()
                if primary not in _VALID_LANG_CODES:
                    is_valid = False
                # Check for obviously invalid region codes (e.g., xx, zz)
                parts = lang_str.split("-")
                if len(parts) > 1:
                    region = parts[1].upper()
                    if len(region) == 2 and not re.match(r"^[A-Z]{2}$", region):
                        is_valid = False

            result.hreflang_tags.append(HreflangEntry(lang=lang_str, url=str(href), is_valid_lang=is_valid))

    if result.hreflang_tags:
        # Check for x-default
        langs = [h.lang for h in result.hreflang_tags]
        if "x-default" not in langs:
            issues.append("Hreflang tags present but missing x-default fallback")
        # Check self-reference
        if url:
            self_urls = [h.url for h in result.hreflang_tags]
            if url not in self_urls and not any(url.rstrip("/") == u.rstrip("/") for u in self_urls):
                issues.append("Hreflang tags don't include self-referencing entry")
        # Check for invalid language codes
        invalid_langs = [h.lang for h in result.hreflang_tags if not h.is_valid_lang]
        if invalid_langs:
            issues.append(
                f"Invalid hreflang language code(s): {', '.join(invalid_langs)}. "
                "Use ISO 639-1 codes (e.g., 'en', 'it', 'en-US')."
            )

    # Favicon
    favicon_selectors = [
        ("link", {"rel": "icon"}),
        ("link", {"rel": "shortcut icon"}),
        ("link", {"rel": "apple-touch-icon"}),
    ]
    for tag_name, attrs in favicon_selectors:
        fav = soup.find(tag_name, attrs=attrs)
        if fav and fav.get("href"):
            result.favicon = str(fav["href"])
            break

    if not result.favicon:
        issues.append("No favicon detected (check /favicon.ico)")

    # Open Graph tags
    for tag in soup.find_all("meta", attrs={"property": True}):
        prop = str(tag.get("property", ""))
        content = str(tag.get("content", ""))
        if prop.startswith("og:"):
            result.og_tags[prop] = content

    if not result.og_tags:
        issues.append(
            "No Open Graph tags found. Add og:title, og:description, og:image, og:url for rich social sharing."
        )
    else:
        for required in ["og:title", "og:description", "og:image", "og:url"]:
            if required not in result.og_tags:
                issues.append(f"Missing {required} tag")

    # Twitter Card tags
    for tag in soup.find_all("meta", attrs={"name": True}):
        name = str(tag.get("name", ""))
        content = str(tag.get("content", ""))
        if name.startswith("twitter:"):
            result.twitter_tags[name] = content

    if not result.twitter_tags:
        issues.append("No Twitter Card tags found. Add twitter:card and twitter:title for Twitter/X previews.")
    else:
        if "twitter:card" not in result.twitter_tags:
            issues.append("Missing twitter:card type (summary, summary_large_image, etc.)")

    # Other meta tags
    for tag in soup.find_all("meta"):
        name = str(tag.get("name", ""))
        content = str(tag.get("content", ""))
        prop = str(tag.get("property", ""))
        if (
            name
            and not name.startswith(("twitter:", "viewport", "description", "robots"))
            and not prop.startswith("og:")
        ):
            result.other_meta[name] = content

    result.issues = issues
    return result


# ── Report formatter ──────────────────────────────────────────


def format_meta_report(analysis: MetaAnalysis) -> str:
    """Format meta analysis as a readable report."""
    lines = ["# Meta Tags Analysis", ""]

    lines.append("## Basic Meta Tags")
    lines.append(f"- **Title**: {analysis.title or 'MISSING'}")
    lines.append(f"  - Length: {analysis.title_length} chars (~{analysis.title_pixel_width}px)")
    lines.append(f"- **Description**: {analysis.description or 'MISSING'}")
    lines.append(f"  - Length: {analysis.description_length} chars (~{analysis.description_pixel_width}px)")
    lines.append(f"- **Canonical**: {analysis.canonical or 'MISSING'}")
    if analysis.canonical:
        lines.append(f"  - Self-referencing: {'Yes' if analysis.canonical_is_self else 'No'}")
    lines.append(f"- **Robots**: {analysis.robots or 'Not set (default: index, follow)'}")
    lines.append(f"- **Viewport**: {analysis.viewport or 'MISSING'}")
    lines.append(f"- **Charset**: {analysis.charset or 'MISSING'}")
    lines.append(f"- **Language**: {analysis.language or 'MISSING'}")
    lines.append(f"- **Favicon**: {analysis.favicon or 'Not found'}")
    lines.append("")

    if analysis.hreflang_tags:
        lines.append("## Hreflang Tags")
        for h in analysis.hreflang_tags:
            lines.append(f"- **{h.lang}**: {h.url}")
        lines.append("")

    if analysis.og_tags:
        lines.append("## Open Graph Tags")
        for k, v in analysis.og_tags.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if analysis.twitter_tags:
        lines.append("## Twitter Card Tags")
        for k, v in analysis.twitter_tags.items():
            lines.append(f"- **{k}**: {v}")
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
