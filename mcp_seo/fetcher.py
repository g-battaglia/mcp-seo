"""HTTP fetching utilities using httpx."""

from __future__ import annotations

import ssl

import httpx
from pydantic import BaseModel


# Create a permissive SSL context to avoid cert issues on some Python installs
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


class FetchResult(BaseModel):
    """Result of an HTTP fetch operation."""

    url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    body: str
    redirect_chain: list[str]
    elapsed_ms: float


def fetch(
    url: str, *, follow_redirects: bool = True, timeout: float = 30.0
) -> FetchResult:
    """Fetch a URL via HTTP and return structured result."""
    redirect_chain: list[str] = []

    with httpx.Client(
        follow_redirects=follow_redirects,
        timeout=timeout,
        verify=_SSL_CONTEXT,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; MCP-SEO/1.0; "
                "+https://github.com/g-battaglia/mcp-seo)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
        event_hooks={"response": [lambda r: redirect_chain.append(str(r.url))]},
    ) as client:
        response = client.get(url)

    return FetchResult(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        body=response.text,
        redirect_chain=redirect_chain[:-1],  # Exclude final URL
        elapsed_ms=response.elapsed.total_seconds() * 1000,
    )


def check_url(url: str, *, timeout: float = 10.0) -> tuple[int, str]:
    """Quick check: returns (status_code, final_url) for a URL."""
    try:
        with httpx.Client(
            follow_redirects=True, timeout=timeout, verify=_SSL_CONTEXT
        ) as client:
            response = client.head(url)
            return response.status_code, str(response.url)
    except httpx.RequestError:
        return 0, url
