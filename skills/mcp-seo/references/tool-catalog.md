# MCP-SEO Tool Catalog

Detailed reference for all tools provided by the mcp-seo package.

---

## Available Tools

### Page Fetching

| CLI Command | MCP Tool | Description |
| --- | --- | --- |
| `mcp-seo crawl <url>` | `crawl` | Render page with headless Chromium, return full HTML |
| `mcp-seo fetch <url>` | `fetch_page` | Fetch raw HTTP response as JSON (headers, status, redirects, SSL info) |

### On-Page SEO

| CLI Command | MCP Tool | Description |
| --- | --- | --- |
| `mcp-seo meta <url>` | `analyze_meta_tags` | Title, description, OG, Twitter, canonical, viewport, hreflang |
| `mcp-seo headings <url>` | `analyze_headings` | Heading hierarchy (h1-h6), single H1 check, skip-level detection |
| `mcp-seo content <url>` | `analyze_content` | Word count, readability, keywords, bigrams, trigrams |
| `mcp-seo images <url>` | `analyze_images` | Alt text, lazy loading, dimensions, WebP/AVIF, srcset, picture element |
| `mcp-seo links <url>` | `analyze_links` | Internal/external count, nofollow/sponsored/ugc, anchor text, broken link check |

### Technical SEO

| CLI Command | MCP Tool | Description |
| --- | --- | --- |
| `mcp-seo headers <url>` | `analyze_headers` | Cache headers, HSTS, CSP, SSL cert validation, cookie security |
| `mcp-seo sitemap <url>` | `analyze_sitemap` | XML sitemap discovery, parsing, validation (50K URL limit, freshness) |
| `mcp-seo robots <url>` | `analyze_robots` | robots.txt parsing, user-agent rules, crawl-delay, sitemap directives |
| `mcp-seo structured-data <url>` | `analyze_structured_data` | JSON-LD, Microdata, RDFa extraction and validation |
| `mcp-seo url-structure <url>` | `analyze_url_structure` | URL length, depth, separators, tracking params, session IDs |

### Performance & Accessibility

| CLI Command | MCP Tool | Description |
| --- | --- | --- |
| `mcp-seo performance <url>` | `analyze_performance` | TTFB, FCP, LCP, CLS, TBT, DOM nodes, requests, resource sizes |
| `mcp-seo mobile <url>` | `analyze_mobile` | Viewport, font sizes, tap targets, horizontal scroll, pinch-to-zoom |
| `mcp-seo accessibility <url>` | `analyze_accessibility` | ARIA landmarks, skip-nav, forms, image alt text, accessibility score |

### Reports

| CLI Command | MCP Tool | Description |
| --- | --- | --- |
| `mcp-seo lighthouse <url>` | `lighthouse_audit` | Lighthouse-style scoring (0-100) with per-category breakdown |
| `mcp-seo report <url>` | `full_seo_report` | Full report combining all analyses |
| `mcp-seo crawl-site <url>` | `crawl_site` | Multi-page crawler with cross-page duplicate detection |

### CLI-Only Utilities

| CLI Command | Description |
| --- | --- |
| `mcp-seo screenshot <url>` | Full-page screenshot saved to `./screenshots/` |
| `mcp-seo og-image -t TITLE -s SUBTITLE` | Generate OG image (1200x630) with custom title and subtitle |
| `mcp-seo setup` | Install Playwright Chromium browser |
| `mcp-seo mcp` | Start MCP server (stdio transport) |

---

## Issue Severity Indicators

- **Critical**: Missing essential elements (title, H1, viewport)
- **Warning**: Suboptimal but not critical (long title, missing OG tags)
- **Pass**: Element present and properly configured

## Lighthouse Scoring

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
- URLs without a scheme (`http://` or `https://`) are automatically prefixed with `https://`
- Network timeouts default to 30 seconds (override with `MCP_SEO_TIMEOUT` env var)
- Failed fetches return meaningful error messages
- Dangerous URL schemes (`file://`, `javascript://`, `data://`) are blocked

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
    ├── images.py            # Image optimization analysis
    ├── headers.py           # HTTP headers analysis
    ├── sitemap.py           # Sitemap discovery & validation
    ├── robots.py            # robots.txt analysis
    ├── structured_data.py   # JSON-LD / Microdata / RDFa extraction
    ├── performance.py       # Core Web Vitals measurement
    ├── content.py           # Content quality analysis
    ├── mobile.py            # Mobile-friendliness analysis
    ├── lighthouse.py        # Lighthouse-style scoring engine
    ├── url_structure.py     # URL structure analysis
    └── accessibility.py     # Accessibility analysis
```
