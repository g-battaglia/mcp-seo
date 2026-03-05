"""Structured data extraction and validation (JSON-LD, Microdata, RDFa) with Schema.org checks."""

from __future__ import annotations

import json

from pydantic import BaseModel

from mcp_seo.utils import get_logger, parse_html

logger = get_logger("structured_data")


# ── Schema.org required properties for Google Rich Results ───

SCHEMA_REQUIRED_PROPERTIES: dict[str, list[str]] = {
    "Article": ["headline", "author", "datePublished", "image"],
    "NewsArticle": ["headline", "author", "datePublished", "image"],
    "BlogPosting": ["headline", "author", "datePublished"],
    "Product": ["name", "image"],
    "Review": ["itemReviewed", "author"],
    "Recipe": ["name", "image"],
    "Event": ["name", "startDate", "location"],
    "LocalBusiness": ["name", "address"],
    "Organization": ["name", "url"],
    "Person": ["name"],
    "FAQPage": ["mainEntity"],
    "HowTo": ["name", "step"],
    "BreadcrumbList": ["itemListElement"],
    "WebSite": ["name", "url"],
    "VideoObject": ["name", "description", "thumbnailUrl", "uploadDate"],
    "JobPosting": ["title", "description", "datePosted", "hiringOrganization"],
    "Course": ["name", "description", "provider"],
    "SoftwareApplication": ["name", "operatingSystem"],
}

# Types that enable Google Rich Results
RICH_RESULT_TYPES = {
    "Article",
    "NewsArticle",
    "BlogPosting",
    "Product",
    "Review",
    "AggregateRating",
    "Recipe",
    "Event",
    "FAQPage",
    "HowTo",
    "BreadcrumbList",
    "VideoObject",
    "JobPosting",
    "Course",
    "LocalBusiness",
    "SoftwareApplication",
    "ItemList",
}


# ── Models ────────────────────────────────────────────────────


class StructuredDataItem(BaseModel):
    format: str  # json-ld, microdata, rdfa
    type: str | None = None
    raw: str
    parsed: dict | list | None = None
    valid: bool = True
    errors: list[str] = []
    missing_properties: list[str] = []
    rich_result_eligible: bool = False


class StructuredDataAnalysis(BaseModel):
    total_items: int = 0
    json_ld_count: int = 0
    microdata_count: int = 0
    rdfa_count: int = 0
    items: list[StructuredDataItem] = []
    schema_types: list[str] = []
    rich_result_types: list[str] = []
    has_website_schema: bool = False
    has_organization_schema: bool = False
    has_breadcrumb: bool = False
    issues: list[str] = []


# ── Schema validation ─────────────────────────────────────────


def _validate_schema_properties(schema_type: str, data: dict) -> tuple[list[str], bool]:
    """Check required properties for a schema type. Returns (missing, is_rich_eligible)."""
    missing: list[str] = []
    required = SCHEMA_REQUIRED_PROPERTIES.get(schema_type, [])

    for prop in required:
        if prop not in data:
            missing.append(prop)

    is_rich = schema_type in RICH_RESULT_TYPES
    return missing, is_rich


def _extract_types_from_jsonld(data: dict | list) -> list[tuple[str, dict]]:
    """Extract all @type entries from JSON-LD data, handling @graph."""
    results: list[tuple[str, dict]] = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                results.extend(_extract_types_from_jsonld(item))
        return results

    if not isinstance(data, dict):
        return results

    # Handle @graph
    if "@graph" in data:
        graph = data["@graph"]
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    results.extend(_extract_types_from_jsonld(item))

    # Handle direct @type
    schema_type = data.get("@type")
    if schema_type:
        if isinstance(schema_type, list):
            for t in schema_type:
                results.append((str(t), data))
        else:
            results.append((str(schema_type), data))

    return results


# ── Main analyzer ─────────────────────────────────────────────


def analyze_structured_data(html: str) -> StructuredDataAnalysis:
    """Extract and analyze structured data from HTML."""
    soup = parse_html(html)
    result = StructuredDataAnalysis()
    issues: list[str] = []
    items: list[StructuredDataItem] = []

    # 1. JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or ""
        if not raw.strip():
            continue

        item = StructuredDataItem(format="json-ld", raw=raw.strip()[:2000])
        try:
            parsed = json.loads(raw)
            item.parsed = parsed
            item.valid = True

            # Extract all types (handles @graph, arrays, nested)
            type_entries = _extract_types_from_jsonld(parsed)
            for schema_type, type_data in type_entries:
                item.type = schema_type
                if schema_type not in result.schema_types:
                    result.schema_types.append(schema_type)

                # Validate required properties
                missing, is_rich = _validate_schema_properties(schema_type, type_data)
                if missing:
                    item.missing_properties = missing
                    issues.append(f"JSON-LD '{schema_type}' missing properties: {', '.join(missing)}")
                if is_rich:
                    item.rich_result_eligible = not bool(missing)
                    if schema_type not in result.rich_result_types:
                        result.rich_result_types.append(schema_type)

                # Track important schema types
                if schema_type == "WebSite":
                    result.has_website_schema = True
                elif schema_type in ("Organization", "LocalBusiness"):
                    result.has_organization_schema = True
                elif schema_type == "BreadcrumbList":
                    result.has_breadcrumb = True

            if not type_entries:
                item.type = "Unknown"

            # Check @context
            if isinstance(parsed, dict) and "@context" not in parsed:
                item.errors.append("Missing @context (should be 'https://schema.org')")
                issues.append("JSON-LD block missing @context")

        except json.JSONDecodeError as e:
            item.valid = False
            item.errors = [f"Invalid JSON: {e}"]
            issues.append(f"Invalid JSON-LD: {e}")

        items.append(item)
        result.json_ld_count += 1

    # 2. Microdata
    for elem in soup.find_all(attrs={"itemscope": True}):
        itemtype = str(elem.get("itemtype", ""))
        raw = str(elem)[:1000]

        schema_type = itemtype.split("/")[-1] if itemtype else "Unknown"
        item = StructuredDataItem(
            format="microdata",
            type=schema_type,
            raw=raw,
        )

        # Extract properties
        props = {}
        for prop_elem in elem.find_all(attrs={"itemprop": True}):
            prop_name = str(prop_elem.get("itemprop", ""))
            prop_value = (
                str(prop_elem.get("content", ""))
                or str(prop_elem.get("href", ""))
                or str(prop_elem.get("src", ""))
                or prop_elem.get_text(strip=True)
            )
            if prop_name:
                props[prop_name] = prop_value

        item.parsed = props
        items.append(item)
        result.microdata_count += 1

        if schema_type and schema_type != "Unknown":
            if schema_type not in result.schema_types:
                result.schema_types.append(schema_type)
            # Validate
            missing, is_rich = _validate_schema_properties(schema_type, props)
            if missing:
                item.missing_properties = missing
            if is_rich:
                item.rich_result_eligible = not bool(missing)
                if schema_type not in result.rich_result_types:
                    result.rich_result_types.append(schema_type)

    # 3. RDFa
    for elem in soup.find_all(attrs={"typeof": True}):
        typeof = str(elem.get("typeof", ""))
        raw = str(elem)[:1000]

        item = StructuredDataItem(
            format="rdfa",
            type=typeof,
            raw=raw,
        )
        items.append(item)
        result.rdfa_count += 1

        if typeof and typeof not in result.schema_types:
            result.schema_types.append(typeof)

    result.items = items
    result.total_items = len(items)

    if result.total_items == 0:
        issues.append("No structured data found on the page")
    else:
        # Recommendations
        if not result.has_website_schema:
            issues.append("Consider adding WebSite schema (enables sitelinks search box)")
        if not result.has_organization_schema:
            issues.append("Consider adding Organization schema (knowledge panel)")
        if not result.has_breadcrumb:
            issues.append("Consider adding BreadcrumbList schema (breadcrumb rich results)")

    result.issues = issues
    return result


# ── Report formatter ──────────────────────────────────────────


def format_structured_data_report(analysis: StructuredDataAnalysis) -> str:
    """Format structured data analysis as a readable report."""
    lines = ["# Structured Data Analysis", ""]

    lines.append(f"**Total items**: {analysis.total_items}")
    lines.append(f"**JSON-LD**: {analysis.json_ld_count}")
    lines.append(f"**Microdata**: {analysis.microdata_count}")
    lines.append(f"**RDFa**: {analysis.rdfa_count}")
    lines.append("")

    if analysis.schema_types:
        lines.append("## Schema Types Found")
        for t in analysis.schema_types:
            rich = " (Rich Result eligible)" if t in RICH_RESULT_TYPES else ""
            lines.append(f"- {t}{rich}")
        lines.append("")

    if analysis.rich_result_types:
        lines.append("## Rich Result Eligible Types")
        for t in analysis.rich_result_types:
            lines.append(f"- {t}")
        lines.append("")

    for i, item in enumerate(analysis.items):
        lines.append(f"## Item {i + 1}: {item.type or 'Unknown'} ({item.format})")
        lines.append(f"**Valid**: {'Yes' if item.valid else 'No'}")
        if item.rich_result_eligible:
            lines.append("**Rich Result**: Eligible")
        if item.missing_properties:
            lines.append(f"**Missing properties**: {', '.join(item.missing_properties)}")
        if item.parsed and isinstance(item.parsed, dict):
            lines.append("```json")
            lines.append(json.dumps(item.parsed, indent=2, ensure_ascii=False)[:1500])
            lines.append("```")
        if item.errors:
            for err in item.errors:
                lines.append(f"- ERROR: {err}")
        lines.append("")

    if analysis.issues:
        lines.append("## Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
