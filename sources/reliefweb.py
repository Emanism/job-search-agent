"""
ReliefWeb source: UN / humanitarian / development-sector jobs.
Free API, no key needed beyond a pre-approved "appname".

Docs: https://apidoc.reliefweb.int/
Request an appname (free, needs approval by email):
https://docs.google.com/forms/d/e/1FAIpQLScR5EE_SBhweLLg_2xMCnXNbT6md4zxqIB00OL0yZWyrqX_Nw/viewform
"""

import requests

API_URL = "https://api.reliefweb.int/v2/jobs"


def _search(appname, query_text, country=None, limit=20):
    """Run one ReliefWeb search and return raw job entries."""
    body = {
        "limit": limit,
        "sort": ["date:desc"],
        "query": {"value": query_text, "operator": "AND"},
        "fields": {"include": ["title", "url_alias", "url", "source", "country", "body"]},
    }
    if country:
        body["filter"] = {"field": "country", "value": country}

    response = requests.post(API_URL, params={"appname": appname}, json=body)
    response.raise_for_status()
    return response.json().get("data", [])


def _normalize(entry):
    fields = entry.get("fields", {})
    sources = fields.get("source", [])
    countries = fields.get("country", [])
    return {
        "title": fields.get("title", "Untitled"),
        "company": sources[0]["name"] if sources else "Unknown organization",
        "location": countries[0]["name"] if countries else "Unspecified",
        "link": fields.get("url") or fields.get("url_alias", ""),
        "description": fields.get("body", ""),
        "source": "ReliefWeb",
    }


def fetch(appname, queries):
    """
    Fetch jobs matching any of `queries` (a list of role keywords) from ReliefWeb.
    Runs two searches per query: one unrestricted (covers remote/worldwide dev-sector
    jobs) and one filtered to Pakistan (covers Islamabad-area jobs specifically),
    since Adzuna can't reach Pakistan directly.
    Returns [] with a warning printed if no appname is configured or the request fails.
    """
    if not appname or appname == "your-approved-reliefweb-appname":
        print("[ReliefWeb] Skipped: no approved RELIEFWEB_APPNAME set in .env")
        return []

    results = []
    query_text = " OR ".join(queries)

    try:
        results += [_normalize(e) for e in _search(appname, query_text)]
        results += [_normalize(e) for e in _search(appname, query_text, country="Pakistan")]
    except requests.exceptions.RequestException as e:
        print(f"[ReliefWeb] Skipped due to error: {e}")
        return []

    return results
