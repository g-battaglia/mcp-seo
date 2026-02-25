"""Robots.txt analysis."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel

from mcp_seo.fetcher import fetch


class RobotsRule(BaseModel):
    user_agent: str
    disallow: list[str] = []
    allow: list[str] = []
    crawl_delay: float | None = None


class RobotsAnalysis(BaseModel):
    found: bool = False
    url: str = ""
    raw_content: str = ""
    rules: list[RobotsRule] = []
    sitemaps: list[str] = []
    issues: list[str] = []


def analyze_robots(base_url: str) -> RobotsAnalysis:
    """Fetch and analyze robots.txt."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = RobotsAnalysis(url=robots_url)
    issues: list[str] = []

    try:
        resp = fetch(robots_url)
    except Exception as e:
        issues.append(f"Failed to fetch robots.txt: {e}")
        result.issues = issues
        return result

    if resp.status_code != 200:
        issues.append(f"robots.txt returned HTTP {resp.status_code}")
        result.issues = issues
        return result

    result.found = True
    result.raw_content = resp.body

    # Parse rules
    current_rule: RobotsRule | None = None
    for line in resp.body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            continue

        directive, _, value = line.partition(":")
        directive = directive.strip().lower()
        value = value.strip()

        if directive == "user-agent":
            if current_rule:
                result.rules.append(current_rule)
            current_rule = RobotsRule(user_agent=value)
        elif directive == "disallow" and current_rule:
            if value:
                current_rule.disallow.append(value)
        elif directive == "allow" and current_rule:
            if value:
                current_rule.allow.append(value)
        elif directive == "crawl-delay" and current_rule:
            try:
                current_rule.crawl_delay = float(value)
            except ValueError:
                pass
        elif directive == "sitemap":
            result.sitemaps.append(value)

    if current_rule:
        result.rules.append(current_rule)

    # Check for issues
    wildcard_rule = next((r for r in result.rules if r.user_agent == "*"), None)
    if not wildcard_rule:
        issues.append("No wildcard (*) user-agent rule found")

    if wildcard_rule and "/" in wildcard_rule.disallow:
        issues.append("robots.txt blocks all crawlers (Disallow: /)")

    if not result.sitemaps:
        issues.append("No sitemap directives in robots.txt")

    result.issues = issues
    return result


def format_robots_report(analysis: RobotsAnalysis) -> str:
    """Format robots.txt analysis as a readable report."""
    lines = ["# Robots.txt Analysis", ""]

    lines.append(f"**URL**: {analysis.url}")
    lines.append(f"**Found**: {'✅ Yes' if analysis.found else '❌ No'}")
    lines.append("")

    if analysis.rules:
        lines.append("## Rules")
        for rule in analysis.rules:
            lines.append(f"\n### User-Agent: `{rule.user_agent}`")
            if rule.disallow:
                for d in rule.disallow:
                    lines.append(f"- Disallow: `{d}`")
            if rule.allow:
                for a in rule.allow:
                    lines.append(f"- Allow: `{a}`")
            if rule.crawl_delay is not None:
                lines.append(f"- Crawl-Delay: {rule.crawl_delay}")
        lines.append("")

    if analysis.sitemaps:
        lines.append("## Sitemaps")
        for s in analysis.sitemaps:
            lines.append(f"- {s}")
        lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
