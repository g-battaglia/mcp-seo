# AGENTS.md — MCP-SEO for Autonomous LLM Agents

## Overview

This project provides a comprehensive set of **SEO analysis tools** designed to be used by an LLM agent autonomously. All tools are accessible via the `mcp-seo` **CLI** or the built-in **MCP server**, and produce structured, markdown-formatted output that is easy for an LLM to parse and reason about.

The tools use a **headless browser (Playwright/Chromium)** for rendering JavaScript-heavy pages, and **httpx** for lightweight HTTP fetching.

---

## Setup

Before using any tools, the agent must run:

```bash
mcp-seo setup
```

This installs the Playwright Chromium browser (one-time only).

---

## Available Tools

### Via CLI

All tools follow the pattern: `mcp-seo <command> <url>`

### Via MCP Server

Start with `mcp-seo mcp` — all tools are exposed as MCP tools that accept a `url` parameter and return Markdown reports.

---

### Page Fetching

| CLI Command              | MCP Tool     | Description                                         |
| ------------------------ | ------------ | --------------------------------------------------- |
| `mcp-seo url-structure <url>`  | `analyze_url_structure`  | URL length, depth, separators, tracking params     |
| `mcp-seo accessibility <url>`  | `analyze_accessibility`  | ARIA landmarks, skip-nav, forms, images, score     |
| `mcp-seo crawl <url>`          | `crawl`                 | Render page with headless Chromium, return full HTML |
| `mcp-seo fetch <url>`   | `fetch_page` | Fetch raw HTTP response as JSON                     |

### On-Page SEO

| CLI Command                     | MCP Tool                  | Description                                          |
| ------------------------------- | ------------------------- | ---------------------------------------------------- |
| `mcp-seo meta <url>`           | `analyze_meta_tags`       | Title, description, OG, Twitter, canonical, viewport |
| `mcp-seo headings <url>`       | `analyze_headings`        | Heading hierarchy (h1-h6), single H1, skip checks   |
| `mcp-seo content <url>`        | `analyze_content`         | Word count, readability, keywords, n-grams           |
| `mcp-seo images <url>`         | `analyze_images`          | Alt text, lazy loading, dimensions, modern formats   |
| `mcp-seo links <url>`          | `analyze_links`           | Internal/external, nofollow, anchor text analysis    |

### Technical SEO

| CLI Command                     | MCP Tool                  | Description                                          |
| ------------------------------- | ------------------------- | ---------------------------------------------------- |
| `mcp-seo headers <url>`        | `analyze_headers`         | Caching, security, compression, redirect chain       |
| `mcp-seo sitemap <url>`        | `analyze_sitemap`         | XML sitemap discovery and validation                 |
| `mcp-seo robots <url>`         | `analyze_robots`          | robots.txt rules, crawl-delay, sitemap directives    |
| `mcp-seo structured-data <url>`| `analyze_structured_data` | JSON-LD, Microdata, RDFa extraction                  |

### Performance

| CLI Command                     | MCP Tool                  | Description                                          |
| ------------------------------- | ------------------------- | ---------------------------------------------------- |
| `mcp-seo performance <url>`    | `analyze_performance`     | TTFB, FCP, LCP, DOM nodes, requests, resource sizes  |
| `mcp-seo mobile <url>`         | `analyze_mobile`          | Viewport, font sizes, tap targets, horizontal scroll |

### Reports

| CLI Command                     | MCP Tool                  | Description                                          |
| ------------------------------- | ------------------------- | ---------------------------------------------------- |
| `mcp-seo crawl-site <url>`     |                         | Crawl entire site, cross-page duplicate detection  |
| `mcp-seo lighthouse <url>`     | `lighthouse_audit`        | Lighthouse-style scoring (0-100) per category        |
| `mcp-seo report <url>`         | `full_seo_report`         | Full report combining all analyses                   |

### Screenshots & Utilities

| CLI Command                     | Description                                          |
| ------------------------------- | ---------------------------------------------------- |
| `mcp-seo screenshot <url>`     | Full-page screenshot saved to `./screenshots/`       |
| `mcp-seo og-image -t T -s S`  | Generate OG image (1200x630) with title & subtitle   |

---

## Recommended Workflow for LLM Agents

### Quick Audit

```
1. mcp-seo lighthouse <url>     -> Get overall SEO score and top issues
2. Focus on lowest-scoring categories
3. Use specific tools to dive deeper
```

### Comprehensive Audit

```
1. mcp-seo report <url>         -> Full analysis of everything
2. mcp-seo performance <url>    -> Core Web Vitals (separate browser session)
3. mcp-seo mobile <url>         -> Mobile-friendliness check
4. mcp-seo sitemap <url>        -> Sitemap health (site-wide)
5. mcp-seo robots <url>         -> Crawling configuration
```

### Competitive Analysis

```
For each competitor URL:
1. mcp-seo meta <url>           -> Compare titles, descriptions, OG tags
2. mcp-seo content <url>        -> Compare word counts, keyword usage
3. mcp-seo structured-data <url> -> Compare schema markup
4. mcp-seo headings <url>       -> Compare content structure
```

### Technical Audit

```
1. mcp-seo headers <url>        -> Security & caching headers
2. mcp-seo performance <url>    -> Core Web Vitals
3. mcp-seo sitemap <url>        -> Sitemap completeness
4. mcp-seo robots <url>         -> Crawl directives
5. mcp-seo mobile <url>         -> Mobile-readiness
```

---

## Output Format

All tools output **Markdown-formatted text** to stdout (CLI) or as MCP tool return values. This makes it easy for LLMs to:

- Parse and understand the results
- Quote specific findings in reports
- Compare results across multiple URLs
- Identify actionable issues

### Issue Severity Indicators

- **Critical**: Missing essential elements (title, H1, viewport)
- **Warning**: Suboptimal but not critical (long title, missing OG tags)
- **Pass**: Element present and properly configured

### Scoring (Lighthouse)

- **90-100**: Good
- **50-89**: Needs improvement
- **0-49**: Poor

---

## Technical Details

- **CLI**: click
- **MCP**: FastMCP (mcp SDK) with stdio transport
- **Browser**: Playwright with headless Chromium
- **HTTP Client**: httpx with redirect tracking
- **HTML Parser**: BeautifulSoup4 + lxml
- **Data Models**: Pydantic v2 for structured output
- **Python**: 3.10+
- **Package Manager**: uv

All analyzers return Pydantic models that can be serialized to JSON for programmatic use, in addition to the formatted markdown reports.

---

## Error Handling

- If Playwright browsers are not installed, run `mcp-seo setup` first
- URLs without a scheme (`http://` or `https://`) will automatically be prefixed with `https://`
- Network timeouts are set to 30 seconds by default (override with `MCP_SEO_TIMEOUT` env var)
- Failed fetches return meaningful error messages
- Dangerous URL schemes (file://, javascript://, data://) are blocked

---

## Project Structure

```
mcp_seo/
├── __init__.py              # Package init (version from importlib.metadata)
├── __main__.py              # python -m mcp_seo entry point
├── cli.py                   # CLI built with click (--output/-o on all commands)
├── mcp_server.py            # MCP server (FastMCP)
├── config.py                # Centralized Config class (env var overrides)
├── browser.py               # Headless browser management (Playwright)
├── fetcher.py               # HTTP fetching utilities (httpx)
├── crawler.py               # Multi-page site crawler with cross-page analysis
├── report.py                # Shared full-report assembly (CLI + MCP)
├── utils.py                 # URL helpers, HTML caching, logging
├── py.typed                 # PEP 561 type marker
└── analyzers/
    ├── __init__.py
    ├── meta.py              # Meta tags analysis
    ├── headings.py          # Heading hierarchy analysis
    ├── links.py             # Link analysis (parallel broken-link checking)
    ├── images.py            # Image optimization analysis (<picture>/<source>)
    ├── headers.py           # HTTP headers analysis
    ├── sitemap.py           # Sitemap discovery & validation (defusedxml)
    ├── robots.py            # robots.txt analysis
    ├── structured_data.py   # JSON-LD / Microdata / RDFa extraction
    ├── performance.py       # Core Web Vitals measurement
    ├── content.py           # Content quality analysis
    ├── mobile.py            # Mobile-friendliness analysis
    ├── lighthouse.py        # Lighthouse-style scoring engine
    ├── url_structure.py     # URL structure analysis (depth, params, keywords)
    └── accessibility.py     # Accessibility analysis (ARIA, landmarks, forms)
```
