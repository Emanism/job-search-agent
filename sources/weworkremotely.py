"""
We Work Remotely source: well-known remote job board. No official search
API, but a public combined RSS feed (all categories) that needs no key.

Two coverage limits, by design:
1. Only the ~100 most recent postings across ALL categories are available
   (no pagination, no per-category server-side search), so this misses
   older listings and may under-represent less recent categories.
2. WWR's `region` field is inconsistent -- sometimes "Anywhere in the
   World", sometimes a bare US state name, sometimes a city with no
   country. To avoid false positives we only keep postings that explicitly
   say worldwide, USA, or UK; a listing that only names a US state or a UK
   city (e.g. "Utah" or "Manchester") will be missed.
"""

import re
import xml.etree.ElementTree as ET

import requests

FEED_URL = "https://weworkremotely.com/remote-jobs.rss"

_LOCATION_RE = re.compile(
    r"\b(Anywhere in the World|Worldwide|USA|United States|UK|United Kingdom)\b",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text):
    return _TAG_RE.sub(" ", text or "").strip()


def _split_title(raw_title):
    """WWR titles are formatted 'Company: Job Title' -- split them apart."""
    if ":" in raw_title:
        company, _, role = raw_title.partition(":")
        return company.strip(), role.strip()
    return "Unknown company", raw_title.strip()


def fetch(queries):
    """
    Fetch the latest WWR postings, keep only ones open worldwide or
    explicitly listing the US/UK, then narrow to ones matching any of
    `queries` by keyword (WWR has no server-side text search, so this
    match happens locally against the title + category).
    """
    try:
        response = requests.get(FEED_URL, headers={"User-Agent": "job-search-agent"})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[WeWorkRemotely] Skipped due to error: {e}")
        return []

    root = ET.fromstring(response.content)
    query_patterns = [re.compile(r"\b" + re.escape(q.lower()) + r"\b") for q in queries]

    results = []
    for item in root.findall(".//item"):
        region = item.findtext("region") or ""
        if not _LOCATION_RE.search(region):
            continue

        raw_title = item.findtext("title") or "Untitled"
        category = item.findtext("category") or ""
        text = f"{raw_title} {category}".lower()
        if not any(pattern.search(text) for pattern in query_patterns):
            continue

        company, role = _split_title(raw_title)
        results.append({
            "title": role,
            "company": company,
            "location": region,
            "link": item.findtext("link") or "",
            "description": _strip_html(item.findtext("description") or "")[:1000],
            "source": "WeWorkRemotely",
        })

    return results
