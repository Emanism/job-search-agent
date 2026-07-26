# Job-Search Agent — Progress

## What we built
A Python project that pulls job listings from **seven sources** (four official
APIs, two curated remote boards, one company-ATS scanner, plus LinkedIn/Indeed/
ZipRecruiter/Glassdoor via scraping), restricts almost all of them to genuinely
remote USA/UK-eligible roles, combines and dedupes everything, matches it
against your CV, prints the best-fit jobs first, and emails you a summary of
the ones above a score threshold. It's live on GitHub and runs automatically
on a schedule via GitHub Actions.

**Files:**
- `main.py` — runs everything: builds/loads your profile, calls every job
  source, dedupes, pre-filters, scores with Claude, prints sorted results,
  emails the winners.
- `sources/adzuna.py` — searches Adzuna (US + UK indexes) for the 4 role
  queries. The "remote" check is now a real filter (the word must actually
  appear in the title/location/description), not just a search-term hint.
- `sources/remotive.py` — curated remote-job board, no key. Filtered to
  postings whose published location eligibility includes the USA, UK, or
  Worldwide (a real field Remotive provides, not a guess).
- `sources/weworkremotely.py` — well-known remote-job board, no key, via its
  public combined RSS feed (~100 most recent postings across all
  categories). Same USA/UK/Worldwide restriction, applied conservatively
  since its `region` field is inconsistent (sometimes a bare US state or
  city with no country).
- `sources/ats.py` + `sources/companies.py` — checks a starter list of ~18
  companies (GitLab, Anthropic, OpenAI, Notion, Stripe, Figma, and others)
  directly on their own Greenhouse/Lever/Ashby job boards — official public
  JSON APIs, no scraping, no ToS concerns. Matches on job **title only**
  (not description — company descriptions routinely mention "AI" as
  marketing boilerplate, which would otherwise match nearly every posting).
  Add more companies any time by editing `sources/companies.py`.
- `sources/jobspy_source.py` — LinkedIn, Indeed, ZipRecruiter, and Glassdoor
  via the `python-jobspy` package. Unlike every other source, this one
  **scrapes** these sites rather than using an official API — a deliberate,
  informed choice (see "Design decisions" below), not a silent default.
  ZipRecruiter and Glassdoor return HTTP 403 (blocked) more often than not
  in practice; when that happens this source just contributes 0 jobs for
  that site rather than failing the run.
- `sources/reliefweb.py` — searches ReliefWeb (UN/development-sector jobs)
  for the same 4 role keywords, plus a second search filtered to Pakistan
  specifically (covers Islamabad). Deliberately **not** restricted to
  remote/USA/UK, since on-the-ground Pakistan roles are the whole point of
  this one.
- `profile.py` — reads `cv.pdf`, sends it to Claude **once** to extract a
  structured profile (skills, years of experience, seniority, target roles,
  preferred locations), and caches it in `profile.json`. Also reads a
  `PROFILE_JSON` environment variable first if set (used by GitHub Actions,
  where cv.pdf/profile.json don't exist on the runner) — falls through to
  the file, then to rebuilding from the CV.
- `matcher.py` — two-stage matching: a free keyword pre-filter caps the
  candidate set (currently 40) regardless of how many jobs the sources
  return, then only those survivors are sent to Claude in batches of 10 for
  0–100 scoring with a reason and any gaps.
- `mailer.py` — emails jobs scoring at or above `SCORE_THRESHOLD` (set in
  `main.py`, currently 40) via Gmail, sorted best-first. Sends nothing if no
  job clears the threshold or if Gmail credentials aren't set.
- `.github/workflows/job-search.yml` — runs `main.py` automatically at 8am
  Pakistan Time (3am UTC) on weekdays, plus a manual "Run workflow" trigger
  for on-demand testing. Reads all credentials and the CV-derived profile
  from GitHub encrypted Secrets (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`,
  `RELIEFWEB_APPNAME`, `ANTHROPIC_API_KEY`, `GMAIL_ADDRESS`,
  `GMAIL_APP_PASSWORD`, `EMAIL_TO`, `PROFILE_JSON`).
- `cv.pdf` / `profile.json` — your CV and its cached structured profile
  (git-ignored, never shared/printed).
- `.env` — all real credentials for local runs (git-ignored, never
  shared/printed). `.env.example` documents the required shape.
- `.gitignore` — keeps `.env`, `cv.pdf`, `profile.json`, `venv/`,
  `.DS_Store`, and local Claude Code settings out of version control.
- `requirements.txt` — reproducible dependency list (now includes
  `python-jobspy` and its dependencies, e.g. `pandas`).

## What's working
- **All seven sources**: fully working, each isolating its own failures
  (bad credentials, blocked scraper, network error) with a warning instead
  of crashing the run.
- **Coverage growth**: went from 79 unique jobs (Adzuna only) → 108 (adding
  Remotive + WeWorkRemotely) → **451 unique jobs** in the latest run, after
  adding the ATS company-board scanner and JobSpy.
- **CV matching**: fully working end-to-end at this new scale — 451 jobs →
  40 survive the free keyword pre-filter → all 40 scored by Claude in
  batches → sorted best-first. Latest run's top result: 92/100, "AI &
  Automation Developer (n8n, Agentic AI, Chatbots)".
- **Email delivery**: fully working via Gmail app password, verified live.
  Latest run emailed 3 matches scoring ≥ 40.
- **Deduplication**: working, keyed by job link across all seven sources.
- **GitHub repo**: live and public at github.com/Emanism/job-search-agent.
  `.env`, `cv.pdf`, and `profile.json` confirmed excluded from every push.
- **GitHub Actions**: live, tested with a successful manual run. Scheduled
  for 8am Pakistan Time on weekdays.

## What's still pending
- **ReliefWeb**: blocked on external approval, not a code issue. Requested
  an appname (`emaan-jobsearch`) via ReliefWeb's form:
  https://docs.google.com/forms/d/e/1FAIpQLScR5EE_SBhweLLg_2xMCnXNbT6md4zxqIB00OL0yZWyrqX_Nw/viewform
  No code changes needed once approved — it'll just start contributing
  results on the next run.

## Design decisions worth remembering
- **JobSpy scrapes, doesn't call an API.** LinkedIn/Indeed/Glassdoor/
  ZipRecruiter's terms of service generally prohibit automated scraping.
  This was an explicit, informed choice (confirmed with you directly) —
  the accepted risk is occasional temporary IP rate-limiting, not legal
  action, for light personal use. If this ever feels like the wrong
  tradeoff, `jobspy_source.py` can be dropped from `main.py`'s source list
  with no effect on anything else.
- **Remote+USA/UK filtering is applied per-source, not globally**, because
  ReliefWeb's Pakistan-specific carve-out would be gutted by a blanket
  "must be remote" rule — that source is intentionally the exception.
- **ATS matching is title-only, not description**, because full-text
  company job descriptions routinely say "AI" as marketing language,
  which would otherwise match nearly every posting at a company (this was
  discovered live: an early version matched 2,247 GitLab jobs before the
  fix, vs. a sane ~15 after).

## How to run it
```
cd ~/Desktop/job-agent
venv/bin/python main.py
```
Or trigger it from GitHub: repo → Actions tab → "Daily Job Search" →
"Run workflow".

## Possible next steps
- **Grow the ATS company list**: `sources/companies.py` currently has ~18
  companies. Add more any time by testing a slug against the relevant
  ATS's public endpoint (documented in that file's docstring).
- **Save results to a file**: results only print to the terminal and get
  emailed above-threshold. Could write every run's full results to a
  CSV/JSON file to track what's been seen or applied to.
- **Refresh the profile**: if your CV changes, delete `profile.json` (or
  pass `force_rebuild=True` to `load_or_build_profile()`) to have it
  re-extracted from the updated `cv.pdf` — and update the `PROFILE_JSON`
  GitHub Secret to match, so the Actions workflow stays in sync.
- **Tune the score threshold**: `SCORE_THRESHOLD` in `main.py` is 40 —
  raise it for a shorter, more selective email; lower it to see more
  borderline matches.
- **Revisit JobSpy** if ZipRecruiter/Glassdoor blocking becomes persistent
  enough to be pure noise — Indeed and LinkedIn have been the reliable
  contributors so far.
