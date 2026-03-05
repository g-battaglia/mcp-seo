"""Centralized configuration with environment variable overrides."""

from __future__ import annotations

import os


class Config:
    """Application-wide configuration.

    All settings can be overridden via environment variables prefixed with
    ``MCP_SEO_``.  For example, ``MCP_SEO_TIMEOUT=60`` sets the default
    HTTP timeout to 60 seconds.
    """

    # ── Timeouts (seconds / milliseconds) ─────────────────────

    @staticmethod
    def http_timeout() -> float:
        """Default HTTP request timeout in seconds."""
        return float(os.environ.get("MCP_SEO_TIMEOUT", "30"))

    @staticmethod
    def browser_timeout() -> int:
        """Default Playwright navigation timeout in milliseconds."""
        return int(os.environ.get("MCP_SEO_BROWSER_TIMEOUT", "30000"))

    @staticmethod
    def ssl_check_timeout() -> float:
        """Timeout for SSL certificate validation checks (seconds)."""
        return float(os.environ.get("MCP_SEO_SSL_TIMEOUT", "5"))

    @staticmethod
    def link_check_timeout() -> float:
        """Timeout for individual broken-link checks (seconds)."""
        return float(os.environ.get("MCP_SEO_LINK_TIMEOUT", "10"))

    # ── Crawler ───────────────────────────────────────────────

    @staticmethod
    def crawler_delay_ms() -> int:
        """Delay between crawler requests in milliseconds."""
        return int(os.environ.get("MCP_SEO_CRAWLER_DELAY_MS", "500"))

    @staticmethod
    def crawler_max_pages() -> int:
        """Default maximum pages for the site crawler."""
        return int(os.environ.get("MCP_SEO_CRAWLER_MAX_PAGES", "50"))

    # ── Caching ───────────────────────────────────────────────

    @staticmethod
    def soup_cache_max_size() -> int:
        """Maximum number of parsed HTML documents to cache."""
        return int(os.environ.get("MCP_SEO_CACHE_SIZE", "32"))

    # ── Concurrency ───────────────────────────────────────────

    @staticmethod
    def link_check_workers() -> int:
        """Number of parallel workers for broken-link checking."""
        return int(os.environ.get("MCP_SEO_LINK_WORKERS", "10"))

    # ── SEO Thresholds ────────────────────────────────────────

    @staticmethod
    def title_max_px() -> int:
        """Google SERP title pixel-width limit."""
        return int(os.environ.get("MCP_SEO_TITLE_MAX_PX", "600"))

    @staticmethod
    def desc_max_px() -> int:
        """Google SERP description pixel-width limit."""
        return int(os.environ.get("MCP_SEO_DESC_MAX_PX", "920"))

    # ── Sitemap ───────────────────────────────────────────────

    @staticmethod
    def max_sub_sitemaps() -> int:
        """Maximum sub-sitemaps to fetch from a sitemap index."""
        return int(os.environ.get("MCP_SEO_MAX_SUB_SITEMAPS", "20"))
