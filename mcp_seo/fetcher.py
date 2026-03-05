"""HTTP fetching utilities using httpx."""

from __future__ import annotations

import ssl

import httpx
from pydantic import BaseModel

from mcp_seo.utils import get_logger

logger = get_logger("fetcher")


# ── SSL Contexts ──────────────────────────────────────────────


def _make_ssl_context(*, verify: bool = True) -> ssl.SSLContext:
    """Create an SSL context with configurable verification."""
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


_SSL_PERMISSIVE = _make_ssl_context(verify=False)
_SSL_STRICT = _make_ssl_context(verify=True)


class FetchResult(BaseModel):
    """Result of an HTTP fetch operation."""

    url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    body: str
    redirect_chain: list[str]
    elapsed_ms: float
    ssl_valid: bool = True
    ssl_error: str | None = None
    http_version: str | None = None


def fetch(
    url: str,
    *,
    follow_redirects: bool = True,
    timeout: float | None = None,
    verify_ssl: bool = False,
) -> FetchResult:
    """Fetch a URL via HTTP and return structured result.

    When verify_ssl=False (default for compatibility), uses a permissive
    SSL context but still attempts a strict check to report SSL issues.
    """
    from mcp_seo.config import Config

    if timeout is None:
        timeout = Config.http_timeout()

    redirect_chain: list[str] = []
    ssl_valid = True
    ssl_error: str | None = None

    # First, attempt a strict SSL check to detect certificate issues
    if not verify_ssl:
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=Config.ssl_check_timeout(),
                verify=_SSL_STRICT,
            ) as strict_client:
                strict_client.head(url)
        except httpx.ConnectError as e:
            ssl_valid = False
            ssl_error = f"SSL certificate error: {e}"
            logger.warning("SSL issue for %s: %s", url, ssl_error)
        except Exception:
            pass  # Non-SSL errors are fine, we'll catch them in the main fetch

    from mcp_seo.config import Config

    if timeout is None:
        timeout = Config.link_check_timeout()

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, verify=_SSL_PERMISSIVE) as client:
            response = client.get(url)

        http_version = getattr(response, "http_version", None) or str(response.extensions.get("http_version", b""))

        logger.debug(
            "Fetched %s -> %d in %.0fms",
            url,
            response.status_code,
            response.elapsed.total_seconds() * 1000,
        )

        return FetchResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.text,
            redirect_chain=redirect_chain[:-1],  # Exclude final URL
            elapsed_ms=response.elapsed.total_seconds() * 1000,
            ssl_valid=ssl_valid,
            ssl_error=ssl_error,
            http_version=http_version if http_version and http_version != "b''" else None,
        )
    except httpx.RequestError as e:
        logger.error("Failed to fetch %s: %s", url, e)
        raise


def check_url(url: str, *, timeout: float | None = None) -> tuple[int, str]:
    """Quick check: returns (status_code, final_url) for a URL."""
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, verify=_SSL_PERMISSIVE) as client:
            response = client.head(url)
            return response.status_code, str(response.url)
    except httpx.RequestError as e:
        logger.debug("URL check failed for %s: %s", url, e)
        return 0, url
