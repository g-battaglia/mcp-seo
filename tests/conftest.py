"""Shared HTML fixtures for tests."""

GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Best Python SEO Tools in 2024 - Complete Guide</title>
    <meta name="description" content="Discover the best Python SEO tools for 2024. This comprehensive guide covers crawlers, analyzers, and automation frameworks for technical SEO.">
    <link rel="canonical" href="https://example.com/seo-tools">
    <link rel="icon" href="/favicon.ico">
    <link rel="alternate" hreflang="en" href="https://example.com/seo-tools">
    <link rel="alternate" hreflang="it" href="https://example.com/it/seo-tools">
    <link rel="alternate" hreflang="x-default" href="https://example.com/seo-tools">
    <meta property="og:title" content="Best Python SEO Tools in 2024">
    <meta property="og:description" content="Complete guide to Python SEO tools">
    <meta property="og:image" content="https://example.com/og.png">
    <meta property="og:url" content="https://example.com/seo-tools">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Best Python SEO Tools in 2024">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Best Python SEO Tools in 2024",
        "author": {"@type": "Person", "name": "John Doe"},
        "datePublished": "2024-01-15",
        "image": "https://example.com/og.png"
    }
    </script>
</head>
<body>
    <header><nav><a href="/">Home</a> <a href="/about">About</a></nav></header>
    <main>
        <h1>Best Python SEO Tools in 2024</h1>
        <p>Python has become a dominant language for SEO professionals who want to automate and scale their workflows. In this guide, we explore the top tools available.</p>
        <h2>Why Python for SEO?</h2>
        <p>Python offers extensive libraries for web scraping, data analysis, and automation. Its simplicity makes it accessible to marketers who are not developers by trade. The ecosystem includes tools for every aspect of technical SEO.</p>
        <h2>Top Crawlers</h2>
        <p>Web crawlers are essential for discovering pages and identifying issues across a website. Tools like Scrapy and Playwright enable sophisticated crawling strategies with JavaScript rendering support.</p>
        <h3>Scrapy</h3>
        <p>Scrapy is a powerful and mature framework for web crawling. It handles concurrency, rate limiting, and data pipelines out of the box.</p>
        <h3>Playwright</h3>
        <p>Playwright enables headless browser automation with Chromium, Firefox, and WebKit. It renders JavaScript and provides accurate DOM snapshots.</p>
        <h2>Analysis Tools</h2>
        <p>Once data is collected, analysis tools help identify patterns and issues. BeautifulSoup and lxml are popular choices for HTML parsing. These libraries provide intuitive APIs for navigating the DOM tree and extracting structured data from complex pages.</p>
        <h3>BeautifulSoup</h3>
        <p>BeautifulSoup is the most popular HTML parsing library in the Python ecosystem. It handles malformed markup gracefully and provides multiple parser backends including lxml and html5lib. For SEO analysis, it excels at extracting meta tags, headings, links, and structured data from any webpage regardless of its HTML quality.</p>
        <h3>Data Processing</h3>
        <p>After parsing, pandas and numpy enable powerful data analysis workflows. SEO professionals can aggregate crawl data, identify patterns in title tags across thousands of pages, and generate comprehensive audit reports. Statistical analysis helps prioritize which issues to fix first based on traffic impact and implementation effort. Machine learning models can even predict which optimizations will yield the greatest ranking improvements.</p>
        <img src="/images/tools.webp" alt="Python SEO tools comparison" width="800" height="400" loading="lazy">
        <img src="/images/chart.avif" alt="Performance chart" width="600" height="300" loading="lazy">
        <a href="https://external.com/resource" rel="nofollow">External resource</a>
        <a href="/contact">Contact us</a>
        <a href="/blog" rel="sponsored">Our blog</a>
        <link rel="next" href="https://example.com/seo-tools?page=2">
    </main>
    <footer><p>Copyright 2024</p></footer>
</body>
</html>"""


BAD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Hi</title>
</head>
<body>
    <h2>Skipped H1</h2>
    <h4>Skipped levels</h4>
    <h2>Skipped H1</h2>
    <img src="/no-alt.jpg">
    <img src="/also-no-alt.png">
    <a href="/page1"></a>
    <a href="/page2"></a>
    <p>Short page.</p>
</body>
</html>"""


MINIMAL_HTML = """<!DOCTYPE html>
<html><head><title>Minimal</title></head><body><p>Hello</p></body></html>"""


STRUCTURED_DATA_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Product Page</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Widget Pro",
        "image": "https://example.com/widget.jpg"
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com"}
        ]
    }
    </script>
    <script type="application/ld+json">
    {"invalid json
    </script>
</head>
<body>
    <div itemscope itemtype="https://schema.org/Organization">
        <span itemprop="name">Acme Corp</span>
        <span itemprop="url">https://acme.com</span>
    </div>
    <h1>Widget Pro</h1>
    <p>A great product.</p>
</body>
</html>"""
