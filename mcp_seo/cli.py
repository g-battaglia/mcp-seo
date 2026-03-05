"""MCP-SEO CLI — built with click."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import click

from mcp_seo.utils import ensure_url, get_html, get_logger

logger = get_logger("cli")


# ── Output helper ─────────────────────────────────────────────


def _output(text: str, output_file: str | None) -> None:
    """Write text to stdout or to a file if --output is specified."""
    if output_file:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        click.echo(f"Output written to: {output_file}", err=True)
    else:
        click.echo(text)


# ── CLI Group ─────────────────────────────────────────────────


@click.group()
@click.version_option(package_name="mcp-seo")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def cli(verbose: bool) -> None:
    """MCP-SEO — Open-source SEO analysis toolkit for AI agents."""
    if verbose:
        import logging

        logging.getLogger("mcp_seo").setLevel(logging.DEBUG)


# ── Setup ─────────────────────────────────────────────────────


@cli.command()
def setup() -> None:
    """Install Playwright Chromium browser (run once after install)."""
    subprocess.run(["playwright", "install", "chromium"], check=True)


# ── Crawl & Fetch ─────────────────────────────────────────────


@cli.command()
@click.argument("url")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def crawl(url: str, output_file: str | None) -> None:
    """Render a page with headless browser and return full HTML."""
    from mcp_seo.browser import render_page_sync

    url = ensure_url(url)
    html = render_page_sync(url)
    _output(html, output_file)


@cli.command("fetch")
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def fetch_cmd(url: str, json_out: bool, output_file: str | None) -> None:
    """Fetch raw HTTP response without JS rendering."""
    from mcp_seo.fetcher import fetch

    url = ensure_url(url)
    result = fetch(url)
    if json_out:
        _output(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), output_file)
    else:
        parts = [
            f"# HTTP Fetch: {url}",
            f"**Status**: {result.status_code}",
            f"**Final URL**: {result.final_url}",
            f"**Content-Type**: {result.headers.get('content-type', 'N/A')}",
            f"**SSL Valid**: {result.ssl_valid}",
            f"**HTTP Version**: {result.http_version or 'N/A'}",
        ]
        if result.redirect_chain:
            parts.append(f"**Redirects**: {len(result.redirect_chain)}")
            for r in result.redirect_chain:
                parts.append(f"  - {r['status']} → {r['url']}")
        if result.ssl_error:
            parts.append(f"**SSL Error**: {result.ssl_error}")
        parts.append(f"\n**Body length**: {len(result.body)} chars")
        _output("\n".join(parts), output_file)


# ── On-Page SEO ───────────────────────────────────────────────


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def meta(url: str, json_out: bool, output_file: str | None) -> None:
    """Analyze meta tags (title, description, OG, Twitter, canonical, hreflang)."""
    from mcp_seo.analyzers.meta import analyze_meta, format_meta_report

    html, final_url = get_html(url)
    result = analyze_meta(html, final_url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_meta_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def headings(url: str, json_out: bool, output_file: str | None) -> None:
    """Analyze heading hierarchy (h1-h6)."""
    from mcp_seo.analyzers.headings import analyze_headings, format_headings_report

    html, _ = get_html(url)
    result = analyze_headings(html)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_headings_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--check-broken", "-b", is_flag=True, help="Check for broken links (slower).")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def links(url: str, check_broken: bool, json_out: bool, output_file: str | None) -> None:
    """Analyze all links (internal, external, broken)."""
    from mcp_seo.analyzers.links import analyze_links, format_links_report

    html, final_url = get_html(url)
    result = analyze_links(html, final_url, check_broken=check_broken)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_links_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def images(url: str, json_out: bool, output_file: str | None) -> None:
    """Audit images (alt text, dimensions, format, lazy loading, srcset)."""
    from mcp_seo.analyzers.images import analyze_images, format_images_report

    html, final_url = get_html(url)
    result = analyze_images(html, final_url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_images_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def content(url: str, json_out: bool, output_file: str | None) -> None:
    """Analyze page content (word count, readability, keywords)."""
    from mcp_seo.analyzers.content import analyze_content, format_content_report

    html, _ = get_html(url)
    result = analyze_content(html)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_content_report(result), output_file)


# ── Technical SEO ─────────────────────────────────────────────


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def headers(url: str, json_out: bool, output_file: str | None) -> None:
    """Inspect HTTP response headers (caching, security, SSL, cookies)."""
    from mcp_seo.analyzers.headers import analyze_headers, format_headers_report
    from mcp_seo.fetcher import fetch

    url = ensure_url(url)
    fetch_result = fetch(url)
    analysis = analyze_headers(
        fetch_result.headers,
        fetch_result.status_code,
        fetch_result.redirect_chain,
        ssl_valid=fetch_result.ssl_valid,
        ssl_error=fetch_result.ssl_error,
        http_version=fetch_result.http_version,
    )
    if json_out:
        _output(analysis.model_dump_json(indent=2), output_file)
    else:
        _output(format_headers_report(analysis), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def sitemap(url: str, json_out: bool, output_file: str | None) -> None:
    """Discover, parse, and validate XML sitemaps."""
    from mcp_seo.analyzers.sitemap import analyze_sitemap, format_sitemap_report

    url = ensure_url(url)
    result = analyze_sitemap(url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_sitemap_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def robots(url: str, json_out: bool, output_file: str | None) -> None:
    """Fetch and analyze robots.txt."""
    from mcp_seo.analyzers.robots import analyze_robots, format_robots_report

    url = ensure_url(url)
    result = analyze_robots(url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_robots_report(result), output_file)


@cli.command("structured-data")
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def structured_data(url: str, json_out: bool, output_file: str | None) -> None:
    """Extract and validate JSON-LD, Microdata, and RDFa structured data."""
    from mcp_seo.analyzers.structured_data import (
        analyze_structured_data,
        format_structured_data_report,
    )

    html, _ = get_html(url)
    result = analyze_structured_data(html)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_structured_data_report(result), output_file)


# ── URL Structure & Accessibility ─────────────────────────────


@cli.command("url-structure")
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def url_structure(url: str, json_out: bool, output_file: str | None) -> None:
    """Analyze URL structure (length, depth, separators, tracking params)."""
    from mcp_seo.analyzers.url_structure import analyze_url_structure, format_url_structure_report

    url = ensure_url(url)
    result = analyze_url_structure(url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_url_structure_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def accessibility(url: str, json_out: bool, output_file: str | None) -> None:
    """Analyze accessibility (ARIA, landmarks, skip-nav, forms, images)."""
    from mcp_seo.analyzers.accessibility import analyze_accessibility, format_accessibility_report

    html, _ = get_html(url)
    result = analyze_accessibility(html)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_accessibility_report(result), output_file)


# ── Performance ───────────────────────────────────────────────


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def performance(url: str, json_out: bool, output_file: str | None) -> None:
    """Measure Core Web Vitals (TTFB, FCP, LCP, CLS, TBT)."""
    from mcp_seo.analyzers.performance import (
        analyze_performance,
        format_performance_report,
    )

    url = ensure_url(url)
    result = analyze_performance(url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_performance_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def mobile(url: str, json_out: bool, output_file: str | None) -> None:
    """Analyze mobile-friendliness (viewport, tap targets, font sizes, interstitials)."""
    from mcp_seo.analyzers.mobile import analyze_mobile, format_mobile_report

    url = ensure_url(url)
    result = analyze_mobile(url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_mobile_report(result), output_file)


# ── Reports ───────────────────────────────────────────────────


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def lighthouse(url: str, json_out: bool, output_file: str | None) -> None:
    """Run a Lighthouse-style SEO audit with category scoring (0-100)."""
    from mcp_seo.analyzers.lighthouse import format_lighthouse_report, run_lighthouse

    html, final_url = get_html(url)
    result = run_lighthouse(html, final_url)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_lighthouse_report(result), output_file)


@cli.command()
@click.argument("url")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def report(url: str, json_out: bool, output_file: str | None) -> None:
    """Generate a comprehensive SEO report combining ALL analyses."""
    from mcp_seo.report import generate_full_report

    def _progress(msg: str) -> None:
        click.echo(msg, err=True)

    markdown, results = generate_full_report(
        url,
        progress_callback=_progress,
    )

    if json_out:
        report_dict: dict[str, object] = {"url": results.url, "date": results.date}
        for field in (
            "headers",
            "meta",
            "headings",
            "links",
            "images",
            "structured_data",
            "content",
            "sitemap",
            "robots",
            "performance",
            "mobile",
            "lighthouse",
        ):
            val = getattr(results, field, None)
            if val is not None:
                report_dict[field] = val.model_dump()
        _output(json.dumps(report_dict, indent=2, ensure_ascii=False), output_file)
    else:
        _output(markdown, output_file)


# ── Site Crawler ──────────────────────────────────────────────


@cli.command("crawl-site")
@click.argument("url")
@click.option("--max-pages", "-n", default=50, help="Maximum pages to crawl.")
@click.option("--json-output", "-j", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--output", "-o", "output_file", default=None, help="Write output to file.")
def crawl_site(url: str, max_pages: int, json_out: bool, output_file: str | None) -> None:
    """Crawl a website and analyze all discovered pages."""
    from mcp_seo.crawler import crawl_site as _crawl
    from mcp_seo.crawler import format_crawl_report

    url = ensure_url(url)
    result = _crawl(url, max_pages=max_pages)
    if json_out:
        _output(result.model_dump_json(indent=2), output_file)
    else:
        _output(format_crawl_report(result), output_file)


# ── Screenshot & OG Image ─────────────────────────────────────


@cli.command()
@click.argument("url")
def screenshot(url: str) -> None:
    """Take a full-page screenshot and save to ./screenshots/."""
    from mcp_seo.browser import take_screenshot_sync

    url = ensure_url(url)
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]
    output_path = str(screenshots_dir / f"{safe_name}_{timestamp}.png")

    take_screenshot_sync(url, output_path)
    click.echo(f"Screenshot saved to: {output_path}")


@cli.command("og-image")
@click.option("--og-output", "-o", "output", default="og-image.png", help="Output file path.")
@click.option("-t", "--title", default="My Project", help="Title text.")
@click.option("-s", "--subtitle", default="Project Subtitle", help="Subtitle text.")
def og_image(output: str, title: str, subtitle: str) -> None:
    """Generate an OG image (1200x630) with customizable title and subtitle."""
    import asyncio
    from html import escape

    safe_title = escape(title)
    safe_subtitle = escape(subtitle)

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
        <h1 class="logo">{safe_title}</h1>
        <p class="subtitle">{safe_subtitle}</p>
    </div>
</body>
</html>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
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
