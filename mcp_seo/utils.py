"""Shared utilities: URL handling, HTML caching, logging setup."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

# ── Logging ───────────────────────────────────────────────────


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for a module."""
    logger = logging.getLogger(f"mcp_seo.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)  # Default; override with env or flag
    return logger


logger = get_logger("utils")


# ── URL helpers ───────────────────────────────────────────────


def ensure_url(url: str) -> str:
    """Ensure URL has a scheme (defaults to https).

    Rejects dangerous schemes (file://, javascript:, data:, etc.).
    """
    url = url.strip()
    # Block dangerous schemes
    _BLOCKED_SCHEMES = ("file:", "javascript:", "data:", "blob:", "vbscript:", "ftp:")
    if any(url.lower().startswith(s) for s in _BLOCKED_SCHEMES):
        raise ValueError(f"Blocked URL scheme: {url}")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


# ── HTML fetching ─────────────────────────────────────────────


def get_html(url: str, *, rendered: bool = True) -> tuple[str, str]:
    """Get HTML from URL. Returns (html, final_url).

    Uses Playwright for rendered pages, httpx for raw fetches.
    """
    from mcp_seo.browser import render_page_sync
    from mcp_seo.fetcher import fetch

    url = ensure_url(url)
    if rendered:
        logger.debug("Rendering page with headless browser: %s", url)
        html = render_page_sync(url)
        return html, url
    else:
        logger.debug("Fetching raw HTTP: %s", url)
        result = fetch(url)
        return result.body, result.final_url


# ── HTML parsing cache ────────────────────────────────────────

# Bounded cache to avoid re-parsing the same HTML multiple times
# during a single report run. Uses hash(html_string) as key for
# content-based identity (safe across GC cycles unlike id()).
# Max size prevents memory leaks in long-running MCP server processes.
_soup_cache: dict[int, BeautifulSoup] = {}


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML with caching — avoids re-parsing the same string."""
    from mcp_seo.config import Config

    key = hash(html)
    if key not in _soup_cache:
        # Evict oldest entries if cache is full
        if len(_soup_cache) >= Config.soup_cache_max_size():
            # Remove the first (oldest) entry
            oldest_key = next(iter(_soup_cache))
            del _soup_cache[oldest_key]
        _soup_cache[key] = BeautifulSoup(html, "lxml")
    return _soup_cache[key]


def parse_html_fresh(html: str) -> BeautifulSoup:
    """Parse HTML without caching — for analyzers that modify the tree."""
    return BeautifulSoup(html, "lxml")


def clear_soup_cache() -> None:
    """Clear the HTML parse cache."""
    _soup_cache.clear()
