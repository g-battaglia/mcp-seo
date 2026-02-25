"""Structured data extraction and validation (JSON-LD, Microdata, RDFa)."""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup
from pydantic import BaseModel


class StructuredDataItem(BaseModel):
    format: str  # json-ld, microdata, rdfa
    type: str | None = None
    raw: str
    parsed: dict | list | None = None
    valid: bool = True
    errors: list[str] = []


class StructuredDataAnalysis(BaseModel):
    total_items: int = 0
    json_ld_count: int = 0
    microdata_count: int = 0
    rdfa_count: int = 0
    items: list[StructuredDataItem] = []
    schema_types: list[str] = []
    issues: list[str] = []


def analyze_structured_data(html: str) -> StructuredDataAnalysis:
    """Extract and analyze structured data from HTML."""
    soup = BeautifulSoup(html, "lxml")
    result = StructuredDataAnalysis()
    issues: list[str] = []
    items: list[StructuredDataItem] = []

    # 1. JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or ""
        if not raw.strip():
            continue

        item = StructuredDataItem(format="json-ld", raw=raw.strip())
        try:
            parsed = json.loads(raw)
            item.parsed = parsed
            item.valid = True

            # Extract @type
            if isinstance(parsed, dict):
                schema_type = parsed.get("@type", "Unknown")
                item.type = schema_type
                if schema_type not in result.schema_types:
                    result.schema_types.append(schema_type)
            elif isinstance(parsed, list):
                for p in parsed:
                    if isinstance(p, dict):
                        schema_type = p.get("@type", "Unknown")
                        item.type = schema_type
                        if schema_type not in result.schema_types:
                            result.schema_types.append(schema_type)
        except json.JSONDecodeError as e:
            item.valid = False
            item.errors = [f"Invalid JSON: {e}"]
            issues.append(f"Invalid JSON-LD: {e}")

        items.append(item)
        result.json_ld_count += 1

    # 2. Microdata
    for elem in soup.find_all(attrs={"itemscope": True}):
        itemtype = elem.get("itemtype", "")
        raw = str(elem)[:500]  # Truncate for readability

        item = StructuredDataItem(
            format="microdata",
            type=itemtype.split("/")[-1] if itemtype else "Unknown",
            raw=raw,
        )

        # Extract properties
        props = {}
        for prop_elem in elem.find_all(attrs={"itemprop": True}):
            prop_name = prop_elem.get("itemprop", "")
            prop_value = (
                prop_elem.get("content")
                or prop_elem.get("href")
                or prop_elem.get("src")
                or prop_elem.get_text(strip=True)
            )
            props[prop_name] = prop_value

        item.parsed = props
        items.append(item)
        result.microdata_count += 1

        if itemtype:
            type_name = itemtype.split("/")[-1]
            if type_name not in result.schema_types:
                result.schema_types.append(type_name)

    # 3. RDFa
    for elem in soup.find_all(attrs={"typeof": True}):
        typeof = elem.get("typeof", "")
        raw = str(elem)[:500]

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

    result.issues = issues
    return result


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
            lines.append(f"- {t}")
        lines.append("")

    for i, item in enumerate(analysis.items):
        lines.append(f"## Item {i + 1}: {item.type or 'Unknown'} ({item.format})")
        lines.append(f"**Valid**: {'✅' if item.valid else '❌'}")
        if item.parsed:
            lines.append("```json")
            lines.append(json.dumps(item.parsed, indent=2, ensure_ascii=False)[:1000])
            lines.append("```")
        if item.errors:
            for err in item.errors:
                lines.append(f"- ❌ {err}")
        lines.append("")

    if analysis.issues:
        lines.append("## ⚠️  Issues Found")
        for issue in analysis.issues:
            lines.append(f"- {issue}")
        lines.append("")

    return "\n".join(lines)
