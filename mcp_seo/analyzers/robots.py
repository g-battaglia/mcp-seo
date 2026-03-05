"""Robots.txt analysis with bot-specific checks and URL blocking test."""

from __future__ import annotations

import contextlib
import re
from urllib.parse import urlparse

from pydantic import BaseModel

from mcp_seo.fetcher import fetch
from mcp_seo.utils import get_logger

logger = get_logger("robots")

# Well-known bot user agents
IMPORTANT_BOTS = {
    "Googlebot": "Google Search",
    "Googlebot-Image": "Google Images",
    "Googlebot-Video": "Google Video",
    "Googlebot-News": "Google News",
    "Bingbot": "Bing Search",
    "Slurp": "Yahoo",
    "DuckDuckBot": "DuckDuckGo",
    "Baiduspider": "Baidu",
    "YandexBot": "Yandex",
    "facebookexternalhit": "Facebook",
    "Twitterbot": "Twitter/X",
}


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

    # New fields
    size_bytes: int = 0
    bot_specific_rules: dict[str, list[str]] = {}  # bot -> disallowed paths
    blocks_important_resources: bool = False
    blocked_resource_paths: list[str] = []

    issues: list[str] = []


def _path_matches(path: str, pattern: str) -> bool:
    """Check if a URL path matches a robots.txt pattern (supports * and $)."""
    if not pattern:
        return False
    # Convert robots.txt pattern to regex
    regex = re.escape(pattern)
    regex = regex.replace(r"\*", ".*")
    regex = regex[:-2] + "$" if regex.endswith(r"\$") else regex + ".*"
    try:
        return bool(re.match(regex, path))
    except re.error:
        return False


def is_url_blocked(rules: list[RobotsRule], url: str, user_agent: str = "*") -> bool:
    """Check if a specific URL is blocked for a given user agent."""
    parsed = urlparse(url)
    path = parsed.path or "/"

    # Find matching rule
    rule = None
    for r in rules:
        if r.user_agent.lower() == user_agent.lower():
            rule = r
            break
    if not rule:
        # Fall back to wildcard
        for r in rules:
            if r.user_agent == "*":
                rule = r
                break
    if not rule:
        return False

    # Check allow first (more specific), then disallow
    for allow_pattern in rule.allow:
        if _path_matches(path, allow_pattern):
            return False
    return any(_path_matches(path, disallow_pattern) for disallow_pattern in rule.disallow)


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
    result.size_bytes = len(resp.body.encode("utf-8"))

    # Google's 500KB limit
    if result.size_bytes > 500 * 1024:
        issues.append(
            f"robots.txt exceeds Google's 500KB limit ({result.size_bytes / 1024:.1f}KB). "
            "Content beyond 500KB is ignored by Googlebot."
        )

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
            with contextlib.suppress(ValueError):
                current_rule.crawl_delay = float(value)
        elif directive == "sitemap":
            result.sitemaps.append(value)

    if current_rule:
        result.rules.append(current_rule)

    # Check for issues
    wildcard_rule = next((r for r in result.rules if r.user_agent == "*"), None)
    if not wildcard_rule:
        issues.append("No wildcard (*) user-agent rule found")

    if wildcard_rule and "/" in wildcard_rule.disallow:
        issues.append("CRITICAL: robots.txt blocks all crawlers (Disallow: /)")

    if not result.sitemaps:
        issues.append("No sitemap directives in robots.txt")

    # Bot-specific analysis
    for bot_name, bot_label in IMPORTANT_BOTS.items():
        for rule in result.rules:
            if rule.user_agent.lower() == bot_name.lower():
                blocked_paths = rule.disallow
                if blocked_paths:
                    result.bot_specific_rules[f"{bot_name} ({bot_label})"] = blocked_paths
                    if "/" in blocked_paths:
                        issues.append(f"CRITICAL: {bot_name} ({bot_label}) is completely blocked")

    # Check if important resources are blocked (CSS/JS)
    important_patterns = ["/css", "/js", "/static", "/assets", "*.css", "*.js"]
    for rule in result.rules:
        if rule.user_agent in ("*", "Googlebot"):
            for disallow in rule.disallow:
                for pattern in important_patterns:
                    if pattern in disallow.lower():
                        result.blocks_important_resources = True
                        result.blocked_resource_paths.append(disallow)
                        break

    if result.blocks_important_resources:
        issues.append(
            f"Blocking important resources (CSS/JS): {', '.join(result.blocked_resource_paths[:5])}. "
            "Googlebot needs these for proper rendering."
        )

    # Contradictory rules check
    for rule in result.rules:
        for allow_path in rule.allow:
            for disallow_path in rule.disallow:
                if allow_path == disallow_path:
                    issues.append(
                        f"Contradictory rules for {rule.user_agent}: Allow and Disallow both set for '{allow_path}'"
                    )

    result.issues = issues
    return result


def format_robots_report(analysis: RobotsAnalysis) -> str:
    """Format robots.txt analysis as a readable report."""
    lines = ["# Robots.txt Analysis", ""]

    lines.append(f"**URL**: {analysis.url}")
    lines.append(f"**Found**: {'Yes' if analysis.found else 'No'}")
    if analysis.size_bytes > 0:
        lines.append(f"**Size**: {analysis.size_bytes / 1024:.1f}KB")
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

    if analysis.bot_specific_rules:
        lines.append("## Bot-Specific Restrictions")
        for bot, paths in analysis.bot_specific_rules.items():
            lines.append(f"- **{bot}**: blocks {', '.join(f'`{p}`' for p in paths[:5])}")
        lines.append("")

    if analysis.sitemaps:
        lines.append("## Sitemaps")
        for s in analysis.sitemaps:
            lines.append(f"- {s}")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
