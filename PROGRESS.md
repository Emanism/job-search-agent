# Job-Search Agent — Progress

## What we built
A Python project that pulls job listings from multiple sources, combines them,
removes duplicates, matches them against your CV, prints the best-fit jobs
first, and emails you a summary of the ones above a score threshold — with a
score, a one-line reason, and any gaps for each.

**Files:**
- `main.py` — runs everything: builds/loads your profile, calls each job
  source, dedupes, pre-filters, scores with Claude, prints sorted results.
- `sources/adzuna.py` — searches Adzuna (US + UK indexes) for "project manager",
  "program manager", "automation", "AI", with "remote" added as a search keyword
  (Adzuna has no real remote/worldwide filter, so this is the practical workaround).
  Also pulls each job's `description` now, used for matching.
- `sources/reliefweb.py` — searches ReliefWeb (UN/development-sector jobs) for the
  same 4 role keywords, plus a second search filtered to Pakistan specifically
  (covers Islamabad, since Adzuna doesn't operate in Pakistan at all). Also
  requests the job `body` text now, used for matching.
- `sources/greenhouse.py` — empty stub for later: company career pages on
  Greenhouse/Lever. Not implemented yet.
- `profile.py` — reads `cv.pdf`, sends it to Claude **once** to extract a
  structured profile (skills, years of experience, seniority, target roles,
  preferred locations), and caches it in `profile.json` so later runs skip
  the PDF read and the API call entirely.
- `matcher.py` — two-stage matching:
  1. `keyword_prefilter()` — free, plain Python. Counts profile-keyword hits
     in each job's title+description, drops zero-hit jobs, caps the survivors
     at 40 — this is what keeps Claude's job-scoring cost bounded no matter
     how many raw jobs come in.
  2. `score_jobs()` — sends only the pre-filtered jobs to Claude, in batches
     of 10 (not one call per job), and gets back a 0–100 score, a one-line
     reason, and any gaps per job, via a strict JSON schema (no manual parsing).
- `mailer.py` — emails a summary of jobs scoring at or above `SCORE_THRESHOLD`
  (set in `main.py`, starts at 40) via Gmail, sorted best-first, with score,
  title, company, location, reason, gaps, and apply link. Sends nothing if no
  job clears the threshold, or if Gmail credentials aren't set — prints a
  clear message either way instead of crashing.
- `cv.pdf` — your CV (git-ignored, never shared/printed).
- `profile.json` — the cached structured profile built from your CV
  (git-ignored, never shared/printed). Delete this file to force a rebuild
  from the CV on the next run.
- `.env` — your real Adzuna keys, ReliefWeb appname, Anthropic API key, and
  Gmail address + app password (never shared/printed).
- `.env.example` — template showing what keys are needed, safe to share.
- `.gitignore` — keeps `.env`, `cv.pdf`, `profile.json`, and `venv/` out of
  version control.
- `requirements.txt` — reproducible list of installed libraries.
- `venv/` — the isolated Python environment for this project.

## What's working
- **Adzuna**: fully working. Last run returned 79 unique remote-tagged jobs
  across the 4 search terms.
- **CV matching**: fully working end-to-end. Last run: 79 jobs → 40 survived
  the free keyword pre-filter → all 40 scored by Claude in 4 batched calls →
  printed sorted best-first (top result was a 48/100 Process Automation
  Business Analyst role, with sensible reasons and gap notes).
- **Deduplication**: working, keyed by job link (falls back to title+company
  if a link is ever missing).
- **Email delivery**: fully working. Uses Gmail's SMTP server with an app
  password (not your real Gmail password — generated at
  myaccount.google.com/apppasswords, requires 2-Step Verification). Verified
  with a live test email received successfully. Sends only jobs scoring >=
  `SCORE_THRESHOLD` (40), sorted best-first; sends nothing if none clear it.
- **Error handling**: if one source fails or isn't configured, it prints a
  warning and the rest of the agent keeps running (doesn't crash).

## What's still pending
- **ReliefWeb**: blocked on external approval, not a code issue. ReliefWeb
  requires every API caller to have a pre-approved "appname" (a rule they added
  Nov 2025). We requested one (`emaan-jobsearch`) via their form:
  https://docs.google.com/forms/d/e/1FAIpQLScR5EE_SBhweLLg_2xMCnXNbT6md4zxqIB00OL0yZWyrqX_Nw/viewform
  Once ReliefWeb approves it by email, no code changes are needed — just
  re-run the agent and ReliefWeb results will start appearing automatically,
  descriptions included, and will be matched against your profile like
  everything else.

## How to run it
```
cd ~/Desktop/job-agent
venv/bin/python main.py
```

## Possible next steps
- **Company career pages (Greenhouse/Lever)**: `sources/greenhouse.py` is a
  stub with the two free per-company JSON endpoints noted in its docstring —
  implementing `fetch()` there and calling it from `main.py` is the next
  source to add.
- **Save results**: right now results only print to the terminal (and above-
  threshold ones get emailed). Could additionally write every run's results
  to a CSV/JSON file so you can track what you've already seen or applied to.
- **Refresh the profile**: if your CV changes, delete `profile.json` (or pass
  `force_rebuild=True` to `load_or_build_profile()`) to have it re-extracted
  from the updated `cv.pdf` on the next run.
- **Tune the score threshold**: `SCORE_THRESHOLD` in `main.py` is currently
  40 — raise it for a shorter, more selective email, or lower it to see more
  borderline matches.
- **Schedule it**: the agent only runs when you run it manually. A cron job
  (or similar scheduler) could run `main.py` daily/weekly so match emails
  show up automatically without you remembering to run it.
