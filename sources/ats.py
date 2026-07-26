"""
ATS (applicant-tracking system) company-board source: checks each company
in sources/companies.py directly on its Greenhouse, Lever, or Ashby job
board. All three are free, official, public JSON APIs -- no key, no
scraping, no ToS concerns.

Unlike the other sources, these are full company job boards with no
search parameter, so every fetched job is matched locally against your
QUERIES by keyword (word-boundary match, so "AI" doesn't false-positive
inside e.g. "email" or "maintain"), against the job TITLE only -- not the
description, since company job descriptions routinely mention "AI" etc.
as marketing boilerplate, which would otherwise match nearly every
posting at a company.

Location filtering is also approximate: a bare "Remote" in the location
string is accepted, which occasionally lets through a job like "Remote,
Bangalore" that isn't actually USA/UK-eligible. The Claude scoring stage
downstream usually catches this and flags it as a location gap.
"""

import html
import re

import requests

from sources.companies import COMPANIES

_TAG_RE = re.compile(r"<[^>]+>")
_LOCATION_RE = re.compile(
    r"\b(Remote|Worldwide|Anywhere|USA|US|United States|UK|United Kingdom|"
    r"Americas|North America)\b",
    re.IGNORECASE,
)


def _clean_html(text):
    return _TAG_RE.sub(" ", html.unescape(text or "")).strip()


def _matches_queries(text, query_patterns):
    text = text.lower()
    return any(pattern.search(text) for pattern in query_patterns)


def _fetch_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    response = requests.get(url, params={"content": "true"})
    response.raise_for_status()
    jobs = []
    for entry in response.json().get("jobs", []):
        jobs.append({
            "title": entry.get("title", "Untitled"),
            "location": (entry.get("location") or {}).get("name", "Unspecified"),
            "link": entry.get("absolute_url", ""),
            "description": _clean_html(entry.get("content", ""))[:1000],
        })
    return jobs


def _fetch_lever(slug):
    url = f"https://api.lever.co/v0/postings/{slug}"
    response = requests.get(url, params={"mode": "json"})
    response.raise_for_status()
    jobs = []
    for entry in response.json():
        categories = entry.get("categories", {})
        jobs.append({
            "title": entry.get("text", "Untitled"),
            "location": categories.get("location", "Unspecified"),
            "link": entry.get("hostedUrl", ""),
            "description": (entry.get("descriptionPlain", "") or "")[:1000],
        })
    return jobs


def _fetch_ashby(slug):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    response = requests.get(url)
    response.raise_for_status()
    jobs = []
    for entry in response.json().get("jobs", []):
        jobs.append({
            "title": entry.get("title", "Untitled"),
            "location": entry.get("location", "Unspecified"),
            "link": entry.get("jobUrl", ""),
            "description": (entry.get("descriptionPlain", "") or "")[:1000],
        })
    return jobs


_FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
}


def fetch(queries, companies=None):
    """
    Check each company in `companies` (defaults to sources/companies.py)
    on its ATS board, keeping only postings matching any of `queries`.
    A single company's failure (bad slug, network error) is skipped with
    a warning -- the rest of the list still runs.
    """
    companies = companies if companies is not None else COMPANIES
    query_patterns = [re.compile(r"\b" + re.escape(q.lower()) + r"\b") for q in queries]

    results = []
    for company in companies:
        fetcher = _FETCHERS.get(company["ats"])
        if fetcher is None:
            print(f"[ATS] Skipped {company['name']}: unknown ats type '{company['ats']}'")
            continue

        try:
            raw_jobs = fetcher(company["slug"])
        except requests.exceptions.RequestException as e:
            print(f"[ATS] Skipped {company['name']} due to error: {e}")
            continue

        for job in raw_jobs:
            # Title only, not description: these are full company boards with
            # no server-side search, and job descriptions routinely mention
            # "AI" etc. as company-boilerplate buzzwords, which would
            # otherwise match nearly every posting at a company.
            if not _matches_queries(job["title"], query_patterns):
                continue
            # Remote + USA/UK filter, same restriction as the other sources.
            if not _LOCATION_RE.search(job["location"]):
                continue
            job["company"] = company["name"]
            job["source"] = "ATS"
            results.append(job)

    return results
