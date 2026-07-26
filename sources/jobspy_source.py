"""
JobSpy source: LinkedIn, Indeed, ZipRecruiter, and Glassdoor via the
python-jobspy package (https://github.com/speedyapply/JobSpy).

Unlike every other source in this project, JobSpy works by SCRAPING these
sites rather than calling an official API -- their terms of service
generally prohibit automated access. This was a deliberate, informed
choice (not a default): the accepted risk is occasional temporary
rate-limiting of your IP, not legal action, for light personal use.

In practice ZipRecruiter and Glassdoor return HTTP 403 ("forbidden") more
often than not. When that happens, JobSpy logs an error for that one site
and returns 0 rows for it rather than crashing -- so this source keeps
working with whichever sites are reachable at the time.
"""

import math

from jobspy import scrape_jobs

SITES = ["indeed", "linkedin", "zip_recruiter", "glassdoor"]


def _clean(value, default=""):
    """Pandas represents a missing text cell as NaN (a float), not None or
    "" -- and NaN is truthy in Python, so a plain `value or default` doesn't
    catch it. Handle that case explicitly."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return value
RESULTS_PER_QUERY = 15

# (search location, Indeed's country code) -- one pass per country, per query.
_COUNTRIES = [
    ("United States", "USA"),
    ("United Kingdom", "UK"),
]


def _fetch_one(query_text, location, country_indeed):
    try:
        df = scrape_jobs(
            site_name=SITES,
            search_term=query_text,
            location=location,
            is_remote=True,
            results_wanted=RESULTS_PER_QUERY,
            country_indeed=country_indeed,
        )
    except Exception as e:
        print(f"[JobSpy] Skipped '{query_text}' in {location} due to error: {e}")
        return []

    jobs = []
    for _, row in df.iterrows():
        jobs.append({
            "title": _clean(row.get("title"), "Untitled"),
            "company": _clean(row.get("company"), "Unknown company"),
            "location": _clean(row.get("location"), location),
            "link": _clean(row.get("job_url"), ""),
            "description": _clean(row.get("description"), "")[:1000],
            "source": f"JobSpy/{_clean(row.get('site'), '?')}",
        })
    return jobs


def fetch(queries):
    """
    Fetch remote jobs matching each of `queries` from LinkedIn, Indeed,
    ZipRecruiter, and Glassdoor, for both the US and UK. A site that's
    currently blocking scrapers just contributes 0 rows for that call
    rather than failing the whole run.
    """
    results = []
    for query_text in queries:
        for location, country_indeed in _COUNTRIES:
            results += _fetch_one(query_text, location, country_indeed)
    return results
