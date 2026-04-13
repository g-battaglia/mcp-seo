---
name: mcp-seo
description: >-
  SEO analysis toolkit with 18 MCP tools and 21 CLI commands. Use when the user
  wants to audit a URL for SEO, analyze meta tags, headings, links, images,
  structured data, performance, Core Web Vitals, mobile-friendliness, accessibility,
  robots.txt, sitemaps, or content quality. Triggers on: "SEO audit," "check my SEO,"
  "analyze this URL," "meta tags," "page speed," "Core Web Vitals," "lighthouse score,"
  "crawl this site," "broken links," "heading structure," "structured data," "schema markup,"
  "robots.txt," "sitemap," "mobile-friendly," "accessibility check," "content analysis,"
  "keyword density," "on-page SEO," "technical SEO," "SEO report," "SEO score,"
  "why am I not ranking," "my traffic dropped," "SEO issues," "SEO health check,"
  "not showing up in Google," "crawl errors," "indexing issues."
license: MIT
metadata:
  version: "1.0.0"
  author: g-battaglia
  requires: "pip install mcp-seo"
---

# MCP-SEO — SEO Analysis Toolkit for AI Agents

You have access to **mcp-seo**, a complete SEO analysis toolkit with 18 MCP tools and 21 CLI commands. Use these tools to perform real analysis on any URL — do not guess or assume SEO issues, run the tools and report actual findings.

## Prerequisites

The user must have mcp-seo installed. If tools fail with "command not found":

```bash
pip install mcp-seo    # Install the package
mcp-seo setup          # Install headless Chromium (one-time)
```

### MCP Server Configuration

If using as an MCP server (Claude Desktop, Cursor, etc.), add to `claude_desktop_config.json`:

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

---

## Tool Reference

If the mcp-seo MCP server is connected, use MCP tool names directly. Otherwise, use CLI commands via bash.

### Page Fetching

| MCP Tool | CLI Command | What it does |
|----------|-------------|--------------|
| `crawl` | `mcp-seo crawl <url>` | Render page with headless Chromium, return full HTML |
| `fetch_page` | `mcp-seo fetch <url>` | Raw HTTP response (headers, status, redirects, SSL) |

### On-Page SEO

| MCP Tool | CLI Command | What it does |
|----------|-------------|--------------|
| `analyze_meta_tags` | `mcp-seo meta <url>` | Title, description, OG, Twitter, canonical, viewport, hreflang |
| `analyze_headings` | `mcp-seo headings <url>` | H1-H6 hierarchy, single H1 check, skip-level detection |
| `analyze_links` | `mcp-seo links <url>` | Internal/external count, nofollow, anchor text, broken links |
| `analyze_images` | `mcp-seo images <url>` | Alt text, lazy loading, dimensions, WebP/AVIF, srcset |
| `analyze_content` | `mcp-seo content <url>` | Word count, Flesch-Kincaid readability, keywords, n-grams |

### Technical SEO

| MCP Tool | CLI Command | What it does |
|----------|-------------|--------------|
| `analyze_headers` | `mcp-seo headers <url>` | Cache headers, HSTS, CSP, SSL cert, cookie security |
| `analyze_sitemap` | `mcp-seo sitemap <url>` | XML sitemap discovery, parsing, validation (50K URL limit) |
| `analyze_robots` | `mcp-seo robots <url>` | robots.txt rules, user-agent blocks, crawl-delay, sitemap directives |
| `analyze_structured_data` | `mcp-seo structured-data <url>` | JSON-LD, Microdata, RDFa extraction and validation |
| `analyze_url_structure` | `mcp-seo url-structure <url>` | URL length, depth, separators, tracking params, session IDs |

### Performance & Accessibility

| MCP Tool | CLI Command | What it does |
|----------|-------------|--------------|
| `analyze_performance` | `mcp-seo performance <url>` | TTFB, FCP, LCP, CLS, TBT, DOM nodes, resource breakdown |
| `analyze_mobile` | `mcp-seo mobile <url>` | Viewport, font sizes, tap targets, horizontal scroll |
| `analyze_accessibility` | `mcp-seo accessibility <url>` | ARIA landmarks, skip-nav, forms, image alt text, score |

### Reports

| MCP Tool | CLI Command | What it does |
|----------|-------------|--------------|
| `lighthouse_audit` | `mcp-seo lighthouse <url>` | Lighthouse-style scoring (0-100) with category breakdown |
| `full_seo_report` | `mcp-seo report <url>` | Comprehensive report combining all analyses |
| `crawl_site` | `mcp-seo crawl-site <url>` | Multi-page crawler with cross-page duplicate detection |

### CLI-Only Utilities

| CLI Command | What it does |
|-------------|--------------|
| `mcp-seo screenshot <url>` | Full-page screenshot to `./screenshots/` |
| `mcp-seo og-image -t TITLE -s SUBTITLE` | Generate OG image (1200x630) |
| `mcp-seo setup` | Install Playwright Chromium browser |

---

## Recommended Workflows

### Quick Audit

```
1. lighthouse_audit <url>          -> Overall score and top issues
2. Focus on lowest-scoring categories
3. Use specific tools to investigate
```

### Comprehensive Audit

```
1. full_seo_report <url>           -> Full analysis of everything
2. analyze_performance <url>       -> Core Web Vitals (separate browser session)
3. analyze_mobile <url>            -> Mobile-friendliness check
4. analyze_sitemap <url>           -> Sitemap health (site-wide)
5. analyze_robots <url>            -> Crawling configuration
```

### Competitive Analysis

```
For each competitor URL:
1. analyze_meta_tags <url>         -> Compare titles, descriptions, OG tags
2. analyze_content <url>           -> Compare word counts, keyword usage
3. analyze_structured_data <url>   -> Compare schema markup
4. analyze_headings <url>          -> Compare content structure
```

### Technical Audit

```
1. analyze_headers <url>           -> Security & caching headers
2. analyze_performance <url>       -> Core Web Vitals
3. analyze_sitemap <url>           -> Sitemap completeness
4. analyze_robots <url>            -> Crawl directives
5. analyze_mobile <url>            -> Mobile-readiness
```

---

## Output Format

All tools return **Markdown-formatted reports** with:

- **Critical**: Missing essential elements (title, H1, viewport)
- **Warning**: Suboptimal but not critical (long title, missing OG tags)
- **Pass**: Element present and properly configured

### Lighthouse Scoring

- **90-100**: Good
- **50-89**: Needs improvement
- **0-49**: Poor

All CLI commands support `--json-output` for JSON and `-o FILE` for file output.

---

## Configuration

All timeouts and thresholds can be overridden via environment variables with the `MCP_SEO_*` prefix (e.g., `MCP_SEO_TIMEOUT`).

---

## Important Notes

1. **Always run the tools** — do not guess SEO issues from page content alone. The tools provide accurate, structured analysis.

2. **Schema markup detection**: `web_fetch` and `curl` cannot reliably detect JSON-LD injected via JavaScript. Use `analyze_structured_data` instead — it renders the page with a headless browser.

3. **Performance tools require a browser session** — `analyze_performance` and `analyze_mobile` launch Chromium. Run them separately from the main report if needed.

4. **URLs are auto-normalized** — URLs without a scheme get `https://` prepended. Dangerous schemes (`file://`, `javascript://`, `data://`) are blocked.

---

## Audit Methodology

For the full SEO audit framework (priority order, checklists, site-type specific issues), see:
- [SEO Audit Methodology](references/seo-audit-methodology.md)
- [AI Writing Detection Patterns](references/ai-writing-detection.md)
- [Full Tool Catalog](references/tool-catalog.md)
