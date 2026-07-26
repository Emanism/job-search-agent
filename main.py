"""
Job-search agent: pulls jobs from multiple sources, combines them, removes
duplicates, matches them against your CV, and prints the best fits first.

Sources:
- Adzuna (mainstream job board, needs app_id/app_key in .env)
- ReliefWeb (UN/development sector, needs an approved appname in .env)
- Greenhouse/Lever company pages (not implemented yet, see sources/greenhouse.py)

Matching:
- profile.py builds/loads a structured candidate profile from cv.pdf (once,
  cached in profile.json).
- matcher.py cheaply pre-filters fetched jobs by keyword overlap, then sends
  only the survivors to Claude to score 0-100 against the profile.

Email:
- mailer.py sends a summary email (via Gmail) of jobs scoring at or above
  SCORE_THRESHOLD below. Sends nothing if no job clears the threshold.

Run with:
    venv/bin/python main.py
"""

import os

from dotenv import load_dotenv

import mailer
import matcher
import profile as candidate_profile
from sources import adzuna, greenhouse, reliefweb

QUERIES = ["project manager", "program manager", "automation", "AI"]

# Only jobs scoring at or above this get emailed to you. Change this number
# any time to make the email more or less selective.
SCORE_THRESHOLD = 40


def combine_and_dedupe(*job_lists):
    """Merge multiple lists of job dicts into one, dropping duplicates."""
    seen = set()
    combined = []

    for jobs in job_lists:
        for job in jobs:
            # Prefer the link as the uniqueness key (each posting has one);
            # fall back to title+company if a source ever omits a link.
            key = job["link"].strip().lower() or f"{job['title'].lower()}|{job['company'].lower()}"
            if key in seen:
                continue
            seen.add(key)
            combined.append(job)

    return combined


def main():
    load_dotenv()  # reads the .env file into the environment for this run

    profile = candidate_profile.load_or_build_profile()

    adzuna_jobs = adzuna.fetch(
        app_id=os.environ.get("ADZUNA_APP_ID"),
        app_key=os.environ.get("ADZUNA_APP_KEY"),
        queries=QUERIES,
    )
    reliefweb_jobs = reliefweb.fetch(
        appname=os.environ.get("RELIEFWEB_APPNAME"),
        queries=QUERIES,
    )
    greenhouse_jobs = greenhouse.fetch(companies=[])  # not implemented yet

    all_jobs = combine_and_dedupe(adzuna_jobs, reliefweb_jobs, greenhouse_jobs)
    print(f"{len(all_jobs)} unique jobs found. Pre-filtering by keyword overlap...")

    candidates = matcher.keyword_prefilter(all_jobs, profile)
    print(f"{len(candidates)} plausible matches. Scoring with Claude...\n")

    scored_jobs = matcher.score_jobs(candidates, profile)
    scored_jobs.sort(key=lambda job: job["score"], reverse=True)

    for job in scored_jobs:
        print(f"[{job['score']}] {job['title']}")
        print(f"  Company:  {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Reason:   {job['reason']}")
        if job["gaps"]:
            print(f"  Gaps:     {job['gaps']}")
        print(f"  Link:     {job['link']}\n")

    mailer.send_match_email(
        scored_jobs,
        threshold=SCORE_THRESHOLD,
        gmail_address=os.environ.get("GMAIL_ADDRESS"),
        gmail_app_password=os.environ.get("GMAIL_APP_PASSWORD"),
        to_address=os.environ.get("EMAIL_TO"),
    )


if __name__ == "__main__":
    main()
