# SEO Audit Methodology

Framework for conducting SEO audits. Use this as a checklist alongside mcp-seo tools.

---

## Audit Priority Order

1. **Crawlability & Indexation** — can search engines find and index it?
2. **Technical Foundations** — is the site fast and functional?
3. **On-Page Optimization** — is content optimized?
4. **Content Quality** — does it deserve to rank?
5. **Authority & Links** — does it have credibility?

---

## Technical SEO Audit

### Crawlability

**Robots.txt** (`analyze_robots`)
- Check for unintentional blocks
- Verify important pages allowed
- Check sitemap reference

**XML Sitemap** (`analyze_sitemap`)
- Exists and accessible
- Contains only canonical, indexable URLs
- Updated regularly
- Proper formatting

**Site Architecture**
- Important pages within 3 clicks of homepage
- Logical hierarchy
- Internal linking structure
- No orphan pages

**Crawl Budget** (for large sites)
- Parameterized URLs under control
- Faceted navigation handled properly
- Infinite scroll with pagination fallback
- Session IDs not in URLs

### Indexation

**Index Status**
- `site:domain.com` check
- Compare indexed vs. expected page count

**Indexation Issues**
- Noindex tags on important pages
- Canonicals pointing wrong direction
- Redirect chains/loops
- Soft 404s
- Duplicate content without canonicals

**Canonicalization**
- All pages have canonical tags
- Self-referencing canonicals on unique pages
- HTTP/HTTPS and www/non-www consistency
- Trailing slash consistency

### Site Speed & Core Web Vitals

**Thresholds** (`analyze_performance`)
- LCP (Largest Contentful Paint): < 2.5s
- INP (Interaction to Next Paint): < 200ms
- CLS (Cumulative Layout Shift): < 0.1

**Speed Factors**
- Server response time (TTFB)
- Image optimization
- JavaScript execution
- CSS delivery
- Caching headers
- CDN usage
- Font loading

### Mobile-Friendliness

(`analyze_mobile`)
- Responsive design
- Tap target sizes
- Viewport configured
- No horizontal scroll
- Same content as desktop

### Security & HTTPS

(`analyze_headers`)
- HTTPS across entire site
- Valid SSL certificate
- No mixed content
- HTTP to HTTPS redirects
- HSTS header

### URL Structure

(`analyze_url_structure`)
- Readable, descriptive URLs
- Keywords in URLs where natural
- Consistent structure
- No unnecessary parameters
- Lowercase and hyphen-separated

---

## On-Page SEO Audit

### Title Tags

(`analyze_meta_tags`)

**Check for:**
- Unique titles for each page
- Primary keyword near beginning
- 50-60 characters (visible in SERP)
- Compelling and click-worthy

**Common issues:**
- Duplicate titles
- Too long (truncated) or too short
- Keyword stuffing
- Missing entirely

### Meta Descriptions

(`analyze_meta_tags`)

**Check for:**
- Unique descriptions per page
- 150-160 characters
- Includes primary keyword
- Clear value proposition and call to action

### Heading Structure

(`analyze_headings`)

**Check for:**
- One H1 per page containing primary keyword
- Logical hierarchy (H1 > H2 > H3)
- Headings describe content, not used for styling
- No skip levels (H1 > H3)

### Content Optimization

(`analyze_content`)

- Keyword in first 100 words
- Related keywords naturally used
- Sufficient depth/length for topic
- Answers search intent

**Thin Content Issues:**
- Pages with little unique content
- Tag/category pages with no value
- Duplicate or near-duplicate content

### Image Optimization

(`analyze_images`)

- Descriptive file names
- Alt text on all images
- Compressed file sizes
- Modern formats (WebP)
- Lazy loading implemented
- Responsive images (srcset)

### Internal Linking

(`analyze_links`)

- Important pages well-linked
- Descriptive anchor text
- No broken internal links
- Reasonable link count per page
- No orphan pages

---

## Content Quality Assessment

### E-E-A-T Signals

**Experience**: First-hand experience, original insights/data, real examples
**Expertise**: Author credentials visible, accurate information, properly sourced
**Authoritativeness**: Recognized in the space, cited by others, industry credentials
**Trustworthiness**: Accurate info, transparent about business, contact info, privacy policy, HTTPS

### Content Depth

- Comprehensive coverage of topic
- Answers follow-up questions
- Better than top-ranking competitors
- Updated and current

---

## Common Issues by Site Type

### SaaS/Product Sites
- Product pages lack content depth
- Blog not integrated with product pages
- Missing comparison/alternative pages
- Feature pages thin on content

### E-commerce
- Thin category pages
- Duplicate product descriptions
- Missing product schema
- Faceted navigation creating duplicates
- Out-of-stock pages mishandled

### Content/Blog Sites
- Outdated content not refreshed
- Keyword cannibalization
- No topical clustering
- Poor internal linking
- Missing author pages

### Local Business
- Inconsistent NAP (Name, Address, Phone)
- Missing local schema
- No Google Business Profile optimization
- Missing location pages

---

## Audit Report Structure

**Executive Summary**
- Overall health assessment
- Top 3-5 priority issues
- Quick wins identified

**Findings** (for each issue)
- **Issue**: What's wrong
- **Impact**: High / Medium / Low
- **Evidence**: How you found it (tool output)
- **Fix**: Specific recommendation
- **Priority**: 1-5

**Prioritized Action Plan**
1. Critical fixes (blocking indexation/ranking)
2. High-impact improvements
3. Quick wins (easy, immediate benefit)
4. Long-term recommendations

---

## Schema Markup Detection Note

`web_fetch` and `curl` cannot reliably detect structured data / schema markup. Many CMS plugins inject JSON-LD via client-side JavaScript, which won't appear in static HTML.

Use `analyze_structured_data` (which renders the page with a headless browser) or Google Rich Results Test for accurate schema detection.
