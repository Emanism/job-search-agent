"""
Adzuna source: mainstream job board, covers ~19 countries (not Pakistan).
Needs a free app_id + app_key from https://developer.adzuna.com/

Note: Adzuna has no true "worldwide remote" filter, and where="remote" is
NOT a real location (confirmed: it silently returns zero results). As a
practical approximation, we search a handful of major country indexes and
add "remote" as a search keyword to surface likely-remote listings, then
apply a real filter afterward: only keep results where "remote" actually
appears (as a whole word) in the title or location, since Adzuna's search
keyword is a relevance hint, not a guarantee every result matches it.
"""

import re

import requests

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

DEFAULT_COUNTRIES = ["us", "gb"]  # restricts results to USA + UK postings

_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)


def _is_remote(job):
    return bool(_REMOTE_RE.search(f"{job['title']} {job['location']} {job.get('description', '')}"))


def _search(app_id, app_key, query_text, country, results_per_page=10):
    """Run one Adzuna search in a given country index and return raw results."""
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": f"{query_text} remote",
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }
    response = requests.get(BASE_URL.format(country=country), params=params)
    response.raise_for_status()
    return response.json().get("results", [])


def _normalize(entry):
    return {
        "title": entry.get("title", "Untitled"),
        "company": entry.get("company", {}).get("display_name", "Unknown company"),
        "location": entry.get("location", {}).get("display_name", "Remote"),
        "link": entry.get("redirect_url", ""),
        "description": entry.get("description", ""),
        "source": "Adzuna",
    }


def fetch(app_id, app_key, queries, countries=None):
    """
    Fetch remote-tagged jobs matching each of `queries` (role keywords),
    searched across `countries` (Adzuna country codes, default US + UK).
    Returns [] with a warning printed if keys are missing or a request fails.
    """
    if not app_id or not app_key or app_id == "your-adzuna-app-id":
        print("[Adzuna] Skipped: ADZUNA_APP_ID / ADZUNA_APP_KEY not set in .env")
        return []

    countries = countries or DEFAULT_COUNTRIES
    results = []

    for query_text in queries:
        for country in countries:
            try:
                raw = _search(app_id, app_key, query_text, country)
                results += [_normalize(e) for e in raw]
            except requests.exceptions.RequestException as e:
                print(f"[Adzuna] Skipped '{query_text}' in {country} due to error: {e}")

    return [job for job in results if _is_remote(job)]
