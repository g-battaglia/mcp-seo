# MCP-SEO

**Open-source SEO analysis toolkit for AI agents.**

MCP-SEO gives any LLM agent — or human — a complete suite of SEO auditing tools, accessible both as a **CLI** and as a **Model Context Protocol (MCP) server**. Point it at a URL and get structured, Markdown-formatted reports on meta tags, headings, links, images, performance, mobile-friendliness, structured data, and more.

## Features

- **21 CLI commands** covering on-page SEO, technical SEO, performance, accessibility, and content analysis
- **18 MCP tools** exposing the same capabilities to any MCP-compatible client (Claude Desktop, Cursor, OpenCode, ...)
- **Headless browser rendering** via Playwright/Chromium for JavaScript-heavy pages
- **Lighthouse-style scoring** (0-100) with per-category breakdowns
- **Multi-page site crawler** with duplicate detection and robots.txt respect
- **Structured output** — every analyzer returns Pydantic models (JSON) and Markdown reports
- **Configurable** — all timeouts and thresholds overridable via `MCP_SEO_*` env vars
- **pip-installable** — `pip install mcp-seo` and you're ready to go

## Installation

```bash
pip install mcp-seo

# Or with pipx for isolated CLI usage
pipx install mcp-seo

# Or directly from GitHub
pip install git+https://github.com/g-battaglia/mcp-seo.git
```

After installing, set up the headless browser (one-time):

```bash
mcp-seo setup
```

## Quick Start

```bash
# Lighthouse-style audit with scoring
mcp-seo lighthouse https://example.com

# Full comprehensive report (all analyzers combined)
mcp-seo report https://example.com

# Individual analyzers
mcp-seo meta https://example.com           # Title, description, OG, Twitter, canonical
mcp-seo headings https://example.com       # Heading hierarchy (h1-h6)
mcp-seo links https://example.com          # Internal/external, nofollow, anchors
mcp-seo images https://example.com         # Alt text, lazy loading, dimensions, format
mcp-seo content https://example.com        # Word count, readability, keywords, n-grams
mcp-seo headers https://example.com        # Caching, security, compression, redirects
mcp-seo sitemap https://example.com        # XML sitemap discovery and validation
mcp-seo robots https://example.com         # robots.txt rules and directives
mcp-seo structured-data https://example.com # JSON-LD, Microdata, RDFa
mcp-seo performance https://example.com    # Core Web Vitals (TTFB, FCP, LCP)
mcp-seo mobile https://example.com         # Viewport, tap targets, font sizes
mcp-seo url-structure https://example.com   # URL length, depth, tracking params
mcp-seo accessibility https://example.com   # ARIA, landmarks, skip-nav, score

# Site crawler
mcp-seo crawl-site https://example.com     # Crawl site, find duplicates

# Page fetching
mcp-seo crawl https://example.com          # Rendered HTML (JS executed)
mcp-seo fetch https://example.com          # Raw HTTP response (JSON)

# Utilities
mcp-seo screenshot https://example.com
mcp-seo og-image -t "Title" -s "Subtitle" -o output.png
```

## MCP Server

MCP-SEO includes a built-in [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes all SEO tools to any MCP-compatible AI client.

```bash
mcp-seo mcp
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-seo": {
      "command": "mcp-seo",
      "args": ["mcp"]
    }
  }
}
```

### OpenCode

Add to your `opencode.json`:

```json
{
  "mcpServers": {
    "mcp-seo": {
      "command": "mcp-seo",
      "args": ["mcp"]
    }
  }
}
```

> If you installed from source with `uv` instead of `pip`, use
> `"command": "uv"` with `"args": ["run", "--directory", "/path/to/mcp-seo", "mcp-seo", "mcp"]`.

### Available MCP Tools

| Tool                      | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| `crawl`                   | Render page with headless Chromium, return full HTML  |
| `fetch_page`              | Fetch raw HTTP response as JSON                      |
| `analyze_meta_tags`       | Title, description, OG, Twitter, canonical, viewport |
| `analyze_headings`        | Heading hierarchy (h1-h6), single H1, skip checks   |
| `analyze_links`           | Internal/external links, nofollow, anchor text       |
| `analyze_images`          | Alt text, lazy loading, dimensions, modern formats   |
| `analyze_content`         | Word count, readability, keywords, n-grams           |
| `analyze_headers`         | Caching, security, compression, redirect chain       |
| `analyze_sitemap`         | XML sitemap discovery and validation                 |
| `analyze_robots`          | robots.txt rules, crawl-delay, sitemap directives    |
| `analyze_structured_data` | JSON-LD, Microdata, RDFa extraction                  |
| `analyze_performance`     | TTFB, FCP, LCP, DOM nodes, requests, resource sizes  |
| `analyze_mobile`          | Viewport, font sizes, tap targets, horizontal scroll |
| `analyze_url_structure`   | URL length, depth, separators, tracking params       |
| `analyze_accessibility`   | ARIA landmarks, skip-nav, forms, images, score       |
| `lighthouse_audit`        | Lighthouse-style scoring (0-100) per category        |
| `full_seo_report`         | Comprehensive report combining all analyses          |
| `crawl_site`              | Multi-page crawler with cross-page analysis          |

## For LLM Agents

MCP-SEO is designed to be used autonomously by AI agents. All tools produce structured Markdown output that is easy to parse, quote, and reason about.

See [AGENTS.md](AGENTS.md) for recommended workflows: quick audits, comprehensive audits, competitive analysis, and technical audits.

## Development

```bash
git clone https://github.com/g-battaglia/mcp-seo.git
cd mcp-seo
uv sync --group dev
uv run mcp-seo setup
uv run mcp-seo --help
```

## Tech Stack

| Component | Library |
|---|---|
| CLI | [click](https://click.palletsprojects.com/) |
| MCP server | [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (mcp SDK) |
| Browser | [Playwright](https://playwright.dev/python/) (headless Chromium) |
| HTTP client | [httpx](https://www.python-httpx.org/) |
| HTML parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) |
| Data models | [Pydantic v2](https://docs.pydantic.dev/) |

## License

[GNU Affero General Public License v3.0](LICENSE)
