"""
Remotive source: curated remote-job board, free public API, no key needed.
Docs: https://remotive.com/api-documentation

Remotive publishes an explicit "candidate_required_location" string per job
(e.g. "USA", "UK", "Worldwide"), so filtering to USA/UK-eligible remote
roles here is a real check against real data, not a keyword guess.
"""

import re

import requests

API_URL = "https://remotive.com/api/remote-jobs"

# Word-boundary match so "US" doesn't false-positive inside e.g. "Australia".
_LOCATION_RE = re.compile(
    r"\b(USA|US|United States|UK|United Kingdom|Worldwide|Northern America)\b",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text):
    """Remotive descriptions are HTML; reduce to plain text for matching/display."""
    return _TAG_RE.sub(" ", text or "").strip()


def _search(query_text):
    response = requests.get(API_URL, params={"search": query_text})
    response.raise_for_status()
    return response.json().get("jobs", [])


def _normalize(entry):
    return {
        "title": entry.get("title", "Untitled"),
        "company": entry.get("company_name", "Unknown company"),
        "location": entry.get("candidate_required_location", "Remote"),
        "link": entry.get("url", ""),
        "description": _strip_html(entry.get("description", ""))[:1000],
        "source": "Remotive",
    }


def fetch(queries):
    """
    Fetch remote jobs matching each of `queries`, keeping only postings
    whose candidate_required_location includes the US, UK, or Worldwide.
    Returns [] with a warning printed (per query) if a request fails.
    """
    results = []

    for query_text in queries:
        try:
            raw = _search(query_text)
        except requests.exceptions.RequestException as e:
            print(f"[Remotive] Skipped '{query_text}' due to error: {e}")
            continue

        for entry in raw:
            if _LOCATION_RE.search(entry.get("candidate_required_location", "")):
                results.append(_normalize(entry))

    return results
