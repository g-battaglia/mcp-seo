"""URL structure analysis: length, depth, keywords, separators, query params."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

from mcp_seo.utils import get_logger

logger = get_logger("url_structure")


class UrlStructureAnalysis(BaseModel):
    """Result of URL structure analysis."""

    url: str = ""
    scheme: str = ""
    netloc: str = ""
    path: str = ""
    path_length: int = 0
    full_length: int = 0
    depth: int = 0  # Number of path segments
    has_trailing_slash: bool = False
    has_query_params: bool = False
    query_param_count: int = 0
    has_fragment: bool = False

    # Structure quality
    uses_hyphens: bool = True
    uses_underscores: bool = False
    has_uppercase: bool = False
    has_double_slashes: bool = False
    has_file_extension: bool = False
    file_extension: str | None = None

    # SEO concerns
    has_session_id: bool = False
    has_tracking_params: bool = False
    tracking_params_found: list[str] = []
    path_keywords: list[str] = []

    issues: list[str] = []


# Common tracking/session parameters that hurt SEO
_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "twclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "affiliate",
    "campaign",
    "adgroup",
    "ad_id",
    "click_id",
}

_SESSION_PARAMS = {
    "sid",
    "session_id",
    "sessionid",
    "phpsessid",
    "jsessionid",
    "aspsessionid",
    "cfid",
    "cftoken",
    "viewstate",
}

_FILE_EXTENSIONS = {
    ".html",
    ".htm",
    ".php",
    ".asp",
    ".aspx",
    ".jsp",
    ".cgi",
    ".pl",
    ".py",
    ".rb",
}


def analyze_url_structure(url: str) -> UrlStructureAnalysis:
    """Analyze URL structure for SEO best practices."""
    parsed = urlparse(url)
    result = UrlStructureAnalysis(
        url=url,
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=parsed.path,
        path_length=len(parsed.path),
        full_length=len(url),
    )

    issues: list[str] = []

    # Depth analysis
    segments = [s for s in parsed.path.split("/") if s]
    result.depth = len(segments)

    # Trailing slash
    result.has_trailing_slash = parsed.path.endswith("/") and len(parsed.path) > 1

    # Query parameters
    query_params = parse_qs(parsed.query)
    result.has_query_params = bool(query_params)
    result.query_param_count = len(query_params)

    # Fragment
    result.has_fragment = bool(parsed.fragment)

    # Separator analysis
    result.uses_underscores = "_" in parsed.path
    result.uses_hyphens = "-" in parsed.path
    result.has_uppercase = any(c.isupper() for c in parsed.path)
    result.has_double_slashes = "//" in parsed.path[1:]  # Ignore scheme

    # File extension
    if segments:
        last_segment = segments[-1]
        for ext in _FILE_EXTENSIONS:
            if last_segment.lower().endswith(ext):
                result.has_file_extension = True
                result.file_extension = ext
                break

    # Extract path keywords (meaningful words from URL segments)
    for segment in segments:
        words = re.findall(r"[a-zA-Z]{3,}", segment.lower())
        result.path_keywords.extend(words)

    # Tracking parameters
    param_keys_lower = {k.lower() for k in query_params}
    found_tracking = param_keys_lower & _TRACKING_PARAMS
    if found_tracking:
        result.has_tracking_params = True
        result.tracking_params_found = sorted(found_tracking)

    # Session IDs
    found_session = param_keys_lower & _SESSION_PARAMS
    if found_session:
        result.has_session_id = True

    # ── Issues ────────────────────────────────────────────────

    if result.full_length > 75:
        issues.append(f"URL is long ({result.full_length} chars). Keep URLs under 75 characters for best SERP display.")

    if result.depth > 4:
        issues.append(f"URL depth is {result.depth} levels. Keep important pages within 3-4 clicks of the homepage.")

    if result.uses_underscores:
        issues.append("URL uses underscores (_). Google recommends hyphens (-) as word separators.")

    if result.has_uppercase:
        issues.append(
            "URL contains uppercase characters. URLs are case-sensitive; use lowercase to avoid duplicate content."
        )

    if result.has_double_slashes:
        issues.append("URL contains double slashes (//). This may indicate a misconfiguration.")

    if result.has_session_id:
        issues.append(
            "CRITICAL: URL contains session ID parameters. This creates duplicate content and wastes crawl budget."
        )

    if result.has_tracking_params:
        issues.append(
            f"URL contains tracking parameters ({', '.join(result.tracking_params_found)}). "
            "Use canonical tags or parameter handling in GSC to prevent indexing."
        )

    if result.has_file_extension and result.file_extension in (".php", ".asp", ".aspx", ".cgi"):
        issues.append(
            f"URL exposes server technology ({result.file_extension}). Use clean URLs without file extensions."
        )

    if result.has_query_params and result.query_param_count > 3:
        issues.append(
            f"URL has {result.query_param_count} query parameters. Excessive parameters can confuse crawlers."
        )

    if not result.path_keywords and result.depth > 0:
        issues.append("URL path contains no recognizable keywords. Descriptive URLs improve click-through rates.")

    result.issues = issues
    return result


def format_url_structure_report(analysis: UrlStructureAnalysis) -> str:
    """Format URL structure analysis as a readable report."""
    lines = ["# URL Structure Analysis", ""]

    lines.append(f"**URL**: `{analysis.url}`")
    lines.append(f"**Length**: {analysis.full_length} chars (path: {analysis.path_length})")
    lines.append(f"**Depth**: {analysis.depth} levels")
    lines.append(f"**Scheme**: {analysis.scheme}")
    lines.append("")

    lines.append("## Structure Details")
    lines.append(f"- **Trailing slash**: {'Yes' if analysis.has_trailing_slash else 'No'}")
    lines.append(f"- **Uses hyphens**: {'Yes' if analysis.uses_hyphens else 'No'}")
    lines.append(f"- **Uses underscores**: {'Yes' if analysis.uses_underscores else 'No'}")
    lines.append(f"- **Has uppercase**: {'Yes' if analysis.has_uppercase else 'No'}")
    lines.append(f"- **File extension**: {analysis.file_extension or 'None (clean URL)'}")
    lines.append("")

    if analysis.path_keywords:
        lines.append(f"**Path keywords**: {', '.join(analysis.path_keywords)}")
        lines.append("")

    if analysis.has_query_params:
        lines.append(f"**Query parameters**: {analysis.query_param_count}")
        if analysis.has_tracking_params:
            lines.append(f"**Tracking params**: {', '.join(analysis.tracking_params_found)}")
        if analysis.has_session_id:
            lines.append("**Session ID detected**: Yes")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            prefix = "CRITICAL:" if issue.startswith("CRITICAL") else "WARNING:"
            lines.append(f"- **{prefix}** {issue}")
        lines.append("")

    return "\n".join(lines)
