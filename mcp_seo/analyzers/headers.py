"""HTTP headers analysis: caching, security, redirects."""

from __future__ import annotations

from pydantic import BaseModel


class HeadersAnalysis(BaseModel):
    """Result of HTTP headers analysis."""

    status_code: int = 0
    content_type: str | None = None
    content_encoding: str | None = None
    cache_control: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    expires: str | None = None
    server: str | None = None
    x_powered_by: str | None = None
    content_security_policy: str | None = None
    strict_transport_security: str | None = None
    x_frame_options: str | None = None
    x_content_type_options: str | None = None
    referrer_policy: str | None = None
    permissions_policy: str | None = None
    x_robots_tag: str | None = None
    all_headers: dict[str, str] = {}
    redirect_chain: list[str] = []
    issues: list[str] = []


def analyze_headers(
    headers: dict[str, str],
    status_code: int = 200,
    redirect_chain: list[str] | None = None,
) -> HeadersAnalysis:
    """Analyze HTTP response headers."""
    result = HeadersAnalysis()
    issues: list[str] = []

    result.status_code = status_code
    result.all_headers = headers
    result.redirect_chain = redirect_chain or []

    def get(name: str) -> str | None:
        # Case-insensitive header lookup
        for k, v in headers.items():
            if k.lower() == name.lower():
                return v
        return None

    result.content_type = get("content-type")
    result.content_encoding = get("content-encoding")
    result.cache_control = get("cache-control")
    result.etag = get("etag")
    result.last_modified = get("last-modified")
    result.expires = get("expires")
    result.server = get("server")
    result.x_powered_by = get("x-powered-by")
    result.content_security_policy = get("content-security-policy")
    result.strict_transport_security = get("strict-transport-security")
    result.x_frame_options = get("x-frame-options")
    result.x_content_type_options = get("x-content-type-options")
    result.referrer_policy = get("referrer-policy")
    result.permissions_policy = get("permissions-policy")
    result.x_robots_tag = get("x-robots-tag")

    # Caching checks
    if not result.cache_control:
        issues.append("Missing Cache-Control header")
    elif "no-cache" in result.cache_control or "no-store" in result.cache_control:
        issues.append("Cache-Control disables caching (may be intentional)")

    if not result.content_encoding:
        issues.append("No content encoding (gzip/brotli) detected — page may not be compressed")

    # Security checks
    if not result.strict_transport_security:
        issues.append("Missing Strict-Transport-Security (HSTS) header")
    if not result.x_content_type_options:
        issues.append("Missing X-Content-Type-Options header")
    if not result.x_frame_options and not result.content_security_policy:
        issues.append("Missing X-Frame-Options or Content-Security-Policy frame-ancestors")
    if not result.referrer_policy:
        issues.append("Missing Referrer-Policy header")

    # Server info leak
    if result.server:
        issues.append(f"Server header exposes technology: '{result.server}'")
    if result.x_powered_by:
        issues.append(f"X-Powered-By header exposes technology: '{result.x_powered_by}'")

    # Redirect chain
    if len(result.redirect_chain) > 2:
        issues.append(f"Long redirect chain ({len(result.redirect_chain)} hops)")

    result.issues = issues
    return result


def format_headers_report(analysis: HeadersAnalysis) -> str:
    """Format headers analysis as a readable report."""
    lines = ["# HTTP Headers Analysis", ""]

    lines.append(f"**Status Code**: {analysis.status_code}")
    lines.append("")

    lines.append("## Caching")
    lines.append(f"- **Cache-Control**: {analysis.cache_control or 'Not set'}")
    lines.append(f"- **ETag**: {analysis.etag or 'Not set'}")
    lines.append(f"- **Last-Modified**: {analysis.last_modified or 'Not set'}")
    lines.append(f"- **Expires**: {analysis.expires or 'Not set'}")
    lines.append(f"- **Content-Encoding**: {analysis.content_encoding or 'Not set'}")
    lines.append("")

    lines.append("## Security Headers")
    lines.append(f"- **HSTS**: {analysis.strict_transport_security or '❌ Not set'}")
    lines.append(f"- **CSP**: {analysis.content_security_policy or '❌ Not set'}")
    lines.append(f"- **X-Frame-Options**: {analysis.x_frame_options or '❌ Not set'}")
    lines.append(f"- **X-Content-Type-Options**: {analysis.x_content_type_options or '❌ Not set'}")
    lines.append(f"- **Referrer-Policy**: {analysis.referrer_policy or '❌ Not set'}")
    lines.append(f"- **Permissions-Policy**: {analysis.permissions_policy or '❌ Not set'}")
    lines.append("")

    if analysis.redirect_chain:
        lines.append("## Redirect Chain")
        for i, url in enumerate(analysis.redirect_chain):
            lines.append(f"  {i + 1}. {url}")
        lines.append("")

    if analysis.x_robots_tag:
        lines.append(f"## X-Robots-Tag: {analysis.x_robots_tag}")
        lines.append("")

    lines.append("## All Headers")
    for k, v in analysis.all_headers.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
