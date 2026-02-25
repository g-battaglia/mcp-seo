"""MCP-SEO CLI — built with click."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import click

from mcp_seo.fetcher import fetch
from mcp_seo.browser import render_page_sync, take_screenshot_sync


def _ensure_url(url: str) -> str:
    """Ensure URL has a scheme."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _get_html(url: str, *, rendered: bool = True) -> tuple[str, str]:
    """Get HTML from URL. Returns (html, final_url)."""
    url = _ensure_url(url)
    if rendered:
        html = render_page_sync(url)
        return html, url
    else:
        result = fetch(url)
        return result.body, result.final_url


# ── CLI Group ─────────────────────────────────────────────────


@click.group()
@click.version_option(package_name="mcp-seo")
def cli() -> None:
    """MCP-SEO — Open-source SEO analysis toolkit for AI agents."""


# ── Setup ─────────────────────────────────────────────────────


@cli.command()
def setup() -> None:
    """Install Playwright Chromium browser (run once after install)."""
    subprocess.run(["playwright", "install", "chromium"], check=True)


# ── Crawl & Fetch ─────────────────────────────────────────────


@cli.command()
@click.argument("url")
def crawl(url: str) -> None:
    """Render a page with headless browser and return full HTML."""
    url = _ensure_url(url)
    html = render_page_sync(url)
    click.echo(html)


@cli.command("fetch")
@click.argument("url")
def fetch_cmd(url: str) -> None:
    """Fetch raw HTTP response without JS rendering."""
    url = _ensure_url(url)
    result = fetch(url)
    click.echo(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


# ── On-Page SEO ───────────────────────────────────────────────


@cli.command()
@click.argument("url")
def meta(url: str) -> None:
    """Analyze meta tags (title, description, OG, Twitter, canonical)."""
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report

    html, final_url = _get_html(url)
    click.echo(format_meta_report(analyze_meta(html, final_url)))


@cli.command()
@click.argument("url")
def headings(url: str) -> None:
    """Analyze heading hierarchy (h1-h6)."""
    from mcp_seo.analyzers.headings import analyze_headings, format_headings_report

    html, _ = _get_html(url)
    click.echo(format_headings_report(analyze_headings(html)))


@cli.command()
@click.argument("url")
def links(url: str) -> None:
    """Analyze all links (internal, external, broken)."""
    from mcp_seo.analyzers.links import analyze_links, format_links_report

    html, final_url = _get_html(url)
    click.echo(format_links_report(analyze_links(html, final_url)))


@cli.command()
@click.argument("url")
def images(url: str) -> None:
    """Audit images (alt text, dimensions, format, lazy loading)."""
    from mcp_seo.analyzers.images import analyze_images, format_images_report

    html, final_url = _get_html(url)
    click.echo(format_images_report(analyze_images(html, final_url)))


@cli.command()
@click.argument("url")
def content(url: str) -> None:
    """Analyze page content (word count, readability, keywords)."""
    from mcp_seo.analyzers.content import analyze_content, format_content_report

    html, _ = _get_html(url)
    click.echo(format_content_report(analyze_content(html)))


# ── Technical SEO ─────────────────────────────────────────────


@cli.command()
@click.argument("url")
def headers(url: str) -> None:
    """Inspect HTTP response headers (caching, security, redirects)."""
    from mcp_seo.analyzers.headers import analyze_headers, format_headers_report

    url = _ensure_url(url)
    result = fetch(url)
    analysis = analyze_headers(
        result.headers, result.status_code, result.redirect_chain
    )
    click.echo(format_headers_report(analysis))


@cli.command()
@click.argument("url")
def sitemap(url: str) -> None:
    """Discover, parse, and validate XML sitemaps."""
    from mcp_seo.analyzers.sitemap import analyze_sitemap, format_sitemap_report

    url = _ensure_url(url)
    click.echo(format_sitemap_report(analyze_sitemap(url)))


@cli.command()
@click.argument("url")
def robots(url: str) -> None:
    """Fetch and analyze robots.txt."""
    from mcp_seo.analyzers.robots import analyze_robots, format_robots_report

    url = _ensure_url(url)
    click.echo(format_robots_report(analyze_robots(url)))


@cli.command("structured-data")
@click.argument("url")
def structured_data(url: str) -> None:
    """Extract and validate JSON-LD, Microdata, and RDFa structured data."""
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data,
        format_structured_data_report,
    )

    html, _ = _get_html(url)
    click.echo(format_structured_data_report(analyze_structured_data(html)))


# ── Performance ───────────────────────────────────────────────


@cli.command()
@click.argument("url")
def performance(url: str) -> None:
    """Measure Core Web Vitals (TTFB, FCP, LCP) and page load metrics."""
    from mcp_seo.analyzers.performance import (
        analyze_performance,
        format_performance_report,
    )

    url = _ensure_url(url)
    click.echo(format_performance_report(analyze_performance(url)))


@cli.command()
@click.argument("url")
def mobile(url: str) -> None:
    """Analyze mobile-friendliness (viewport, tap targets, font sizes)."""
    from mcp_seo.analyzers.mobile import analyze_mobile, format_mobile_report

    url = _ensure_url(url)
    click.echo(format_mobile_report(analyze_mobile(url)))


# ── Reports ───────────────────────────────────────────────────


@cli.command()
@click.argument("url")
def lighthouse(url: str) -> None:
    """Run a Lighthouse-style SEO audit with category scoring (0-100)."""
    from mcp_seo.analyzers.lighthouse import run_lighthouse, format_lighthouse_report

    html, final_url = _get_html(url)
    click.echo(format_lighthouse_report(run_lighthouse(html, final_url)))


@cli.command()
@click.argument("url")
def report(url: str) -> None:
    """Generate a comprehensive SEO report combining all analyses."""
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report
    from mcp_seo.analyzers.headings import analyze_headings, format_headings_report
    from mcp_seo.analyzers.links import analyze_links, format_links_report
    from mcp_seo.analyzers.images import analyze_images, format_images_report
    from mcp_seo.analyzers.headers import analyze_headers, format_headers_report
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data,
        format_structured_data_report,
    )
    from mcp_seo.analyzers.content import analyze_content, format_content_report
    from mcp_seo.analyzers.lighthouse import run_lighthouse, format_lighthouse_report

    url = _ensure_url(url)
    click.echo(f"# Comprehensive SEO Report")
    click.echo(f"**URL**: {url}")
    click.echo(f"**Date**: {datetime.now().isoformat()}")
    click.echo("")

    # 1. HTTP headers
    click.echo("Analyzing HTTP headers...")
    fetch_result = fetch(url)
    headers_analysis = analyze_headers(
        fetch_result.headers, fetch_result.status_code, fetch_result.redirect_chain
    )
    click.echo(format_headers_report(headers_analysis))

    # 2. Render page
    click.echo("Rendering page with headless browser...")
    html = render_page_sync(url)
    final_url = url

    # 3-8. Analyzers
    click.echo(format_meta_report(analyze_meta(html, final_url)))
    click.echo(format_headings_report(analyze_headings(html)))
    click.echo(format_links_report(analyze_links(html, final_url)))
    click.echo(format_images_report(analyze_images(html, final_url)))
    click.echo(format_structured_data_report(analyze_structured_data(html)))
    click.echo(format_content_report(analyze_content(html)))

    # 9. Lighthouse
    click.echo(format_lighthouse_report(run_lighthouse(html, final_url)))

    click.echo("---")
    click.echo("Report complete. Use individual commands for deeper analysis.")


# ── Screenshot & OG Image ─────────────────────────────────────


@cli.command()
@click.argument("url")
def screenshot(url: str) -> None:
    """Take a full-page screenshot and save to ./screenshots/."""
    url = _ensure_url(url)
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = (
        url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]
    )
    output_path = str(screenshots_dir / f"{safe_name}_{timestamp}.png")

    take_screenshot_sync(url, output_path)
    click.echo(f"Screenshot saved to: {output_path}")


@cli.command("og-image")
@click.option("-o", "--output", default="og-image.png", help="Output file path.")
@click.option("-t", "--title", default="My Project", help="Title text.")
@click.option("-s", "--subtitle", default="Project Subtitle", help="Subtitle text.")
def og_image(output: str, title: str, subtitle: str) -> None:
    """Generate an OG image (1200x630) with customizable title and subtitle."""
    import asyncio

    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            width: 1200px; height: 630px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: white; position: relative; overflow: hidden;
        }}
        .bg-glow {{
            position: absolute; width: 600px; height: 600px; border-radius: 50%;
            top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%);
            pointer-events: none;
        }}
        .content {{ position: relative; z-index: 10; text-align: center; padding: 40px; }}
        .logo {{
            font-size: 72px; font-weight: 700; letter-spacing: -2px; margin-bottom: 16px;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }}
        .subtitle {{ font-size: 28px; font-weight: 400; color: #94a3b8; letter-spacing: 0.5px; }}
    </style>
</head>
<body>
    <div class="bg-glow"></div>
    <div class="content">
        <h1 class="logo">{title}</h1>
        <p class="subtitle">{subtitle}</p>
    </div>
</body>
</html>"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html_template)
        temp_html = f.name

    try:

        async def capture() -> None:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1200, "height": 630},
                    device_scale_factor=2,
                )
                page = await context.new_page()
                await page.goto(f"file://{temp_html}")
                await page.wait_for_timeout(500)
                await page.screenshot(path=output, type="png")
                await context.close()
                await browser.close()

        asyncio.run(capture())
        click.echo(f"OG image saved to: {output}")
    finally:
        os.unlink(temp_html)


# ── MCP Server launcher ──────────────────────────────────────


@cli.command("mcp")
def mcp_cmd() -> None:
    """Start the MCP-SEO server (stdio transport)."""
    from mcp_seo.mcp_server import mcp

    mcp.run()


# ── Entry point ───────────────────────────────────────────────


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
