# Job-Search Agent

A Python agent that pulls job listings from seven sources, deduplicates them, ranks them against a candidate's CV using Claude, and emails a summary of the best matches — without sending every fetched job to an LLM. Runs locally or on a schedule via GitHub Actions.

## What it does

1. **Fetches** jobs from seven sources in parallel role searches (see [Sources](#sources)).
2. **Deduplicates** the combined results by posting URL.
3. **Builds a candidate profile** from a CV (PDF) once, via Claude, and caches it — skills, seniority, target roles, preferred locations.
4. **Pre-filters** the job list against that profile using plain keyword overlap — no API calls.
5. **Scores** only the surviving candidates with Claude (0–100, with a one-line reason and any gaps), batched to minimize requests.
6. **Prints** results sorted best-match-first.
7. **Emails** a summary of jobs scoring at or above a configurable threshold — nothing is sent if no job clears it.

## Sources

| Source | Type | Remote/USA/UK filter |
|---|---|---|
| [Adzuna](https://developer.adzuna.com/) | Official API (key required) | Yes — word "remote" must appear in title/location/description |
| [Remotive](https://remotive.com/api-documentation) | Official API (no key) | Yes — explicit location-eligibility field |
| [We Work Remotely](https://weworkremotely.com/) | Public RSS feed (no key) | Yes, conservatively — see caveat below |
| Greenhouse / Lever / Ashby | Official per-company public APIs (no key) | Yes — checked per company |
| LinkedIn / Indeed / ZipRecruiter / Glassdoor ([JobSpy](https://github.com/speedyapply/JobSpy)) | **Scraping**, not an official API | Yes, by search parameters |
| [ReliefWeb](https://apidoc.reliefweb.int/) | Official API (approved appname required) | **No** — intentionally also covers Pakistan-based roles |

Each source is an independent module exposing a single `fetch()` function that returns a common shape (`title`, `company`, `location`, `link`, `description`, `source`). Adding a new source is a matter of writing one new module with that interface — no changes required elsewhere.

**A note on JobSpy:** this is the one source in the project that scrapes job sites rather than calling an official API — LinkedIn, Indeed, Glassdoor, and ZipRecruiter's terms of service generally prohibit automated scraping. This is a deliberate, disclosed tradeoff, not a hidden default: the practical risk is occasional temporary rate-limiting of the requesting IP, not legal exposure, for light personal use. In practice ZipRecruiter and Glassdoor return HTTP 403 more often than not; when that happens the source contributes 0 jobs for that site and the run continues normally. If you'd rather not accept that tradeoff, remove the `jobspy_source` import and its `fetch()` call from `main.py` — nothing else depends on it.

**A note on the ATS company-board source:** it can only check companies you tell it about — `sources/companies.py` ships with a starter list of ~18 companies known to hire remote PM/automation/AI talent (GitLab, Anthropic, OpenAI, Notion, Stripe, and others), verified live against their Greenhouse/Lever/Ashby boards. Extend the list any time; the file's docstring shows how to verify a new company's slug before adding it.

## Architecture

```
  ┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
  │ Adzuna │ │ Remotive │ │WeWorkRemotely│ │ ATS company │ │  JobSpy (LI/ │
  │        │ │          │ │              │ │   boards    │ │Indeed/ZR/GD) │
  └───┬────┘ └────┬─────┘ └──────┬───────┘ └──────┬──────┘ └──────┬───────┘
      │           │              │                │               │
      │                    ┌─────┴──────┐                         │
      │                    │ ReliefWeb  │                         │
      │                    │(not remote-│                         │
      │                    │ restricted)│                         │
      │                    └─────┬──────┘                         │
      └───────────┬──────────────┴────────────────┬───────────────┘
                   ▼                               ▼
                          combine + dedupe (by URL)
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │  keyword pre-filter (free)   │  ← plain Python, no API call
                  │  scores by profile-keyword    │
                  │  overlap, caps candidate set  │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌─────────────────────────────┐
                  │   Claude scoring (batched)   │  ← only survivors reach here
                  │  0–100 + reason + gaps        │
                  └──────────────┬───────────────┘
                                 ▼
                       sorted, ranked results
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │   email (score >= threshold) │  ← sends nothing if 0 qualify
                  └─────────────────────────────┘
```

### Two-stage matching: why costs stay bounded

Sending every fetched job's description to an LLM for scoring doesn't scale — cost grows linearly with how many jobs your sources happen to return, which is fully outside your control (this project's job count grew from ~80 to 450+ as sources were added). This project splits matching into two stages instead:

- **Stage 1 — keyword pre-filter (free).** The candidate profile's skills and target roles are reduced to a keyword set; every fetched job is scored by simple keyword overlap in plain Python. Zero-overlap jobs are dropped, and the survivors are capped at a fixed ceiling before anything reaches the LLM.
- **Stage 2 — Claude scoring (paid, but bounded).** Only the capped, pre-filtered candidate set is sent to Claude, in batches (10 jobs per request, not one request per job) using structured output (a JSON schema), so parsing is exact and there's no free-text cleanup step.

The result: however many jobs the sources return, the number actually scored by Claude — and therefore the API spend per run — stays capped by a single constant.

The CV → candidate-profile extraction is a **one-time** Claude call, cached to disk (`profile.json`). It's only repeated if the cache is deleted or a rebuild is explicitly requested — normal runs don't touch the CV or the LLM for profile building at all.

### Email delivery

After scoring, jobs at or above a configurable threshold (`SCORE_THRESHOLD` in `main.py`, default 40) are emailed via Gmail's SMTP server, sorted best-first with score, title, company, location, reason, gaps, and apply link. If nothing clears the threshold, no email is sent. Delivery uses a Gmail **app password** (a revocable, purpose-specific credential — not the account's real password).

## Project structure

```
main.py                    orchestrates: build/load profile → fetch (all sources) → dedupe → pre-filter → score → print → email
profile.py                 extracts CV text (PDF) and builds/caches the structured candidate profile
matcher.py                 keyword pre-filter + batched Claude scoring
mailer.py                  emails jobs scoring >= threshold via Gmail; sends nothing if none qualify
sources/
  adzuna.py                 Adzuna job board, real remote+USA/UK filter
  remotive.py                Remotive, filtered by its location-eligibility field
  weworkremotely.py          We Work Remotely, via public RSS feed
  ats.py + companies.py      Greenhouse/Lever/Ashby company boards
  jobspy_source.py           LinkedIn/Indeed/ZipRecruiter/Glassdoor via scraping
  reliefweb.py                ReliefWeb (UN/development sector, incl. Pakistan)
.github/workflows/
  job-search.yml             GitHub Actions: runs main.py 8am PKT on weekdays
requirements.txt            pinned dependencies
.env.example                 template for required environment variables
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/Emanism/job-search-agent
cd job-search-agent

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
# then fill in .env with your own credentials (see below)
```

### Environment variables (`.env`)

| Variable | Required | Where to get it |
|---|---|---|
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | For Adzuna results | Free account at [developer.adzuna.com](https://developer.adzuna.com/) |
| `RELIEFWEB_APPNAME` | For ReliefWeb results | Requires a pre-approved appname — [request form](https://docs.google.com/forms/d/e/1FAIpQLScR5EE_SBhweLLg_2xMCnXNbT6md4zxqIB00OL0yZWyrqX_Nw/viewform) |
| `ANTHROPIC_API_KEY` | For profile building and scoring | [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys |
| `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` | For email delivery | See [Email setup](#email-setup) below |
| `EMAIL_TO` | Optional | Recipient address; defaults to `GMAIL_ADDRESS` (emails itself) if left blank |

Any source (or the mailer) missing its credentials is skipped with a warning — the agent still runs on whatever's configured, rather than failing outright. Remotive, WeWorkRemotely, the ATS company-board source, and JobSpy need no credentials at all.

### Email setup

1. Enable **2-Step Verification** on the Google account, if not already on: `myaccount.google.com/security`.
2. Go to `myaccount.google.com/apppasswords`, name the app (e.g. `job-agent`), and create it.
3. Copy the 16-character code shown (it's displayed once) into `GMAIL_APP_PASSWORD` in `.env`.
4. Set `GMAIL_ADDRESS` to the full Gmail address the app password belongs to.

### CV

Place a CV as `cv.pdf` in the project root. It's read once to build `profile.json`; both are excluded from version control via `.gitignore`.

## Usage

```bash
venv/bin/python main.py
```

Output is printed to stdout, sorted best-match-first. If Gmail credentials are configured, jobs at or above `SCORE_THRESHOLD` are also emailed in the same format.

## Running on a schedule (GitHub Actions)

`.github/workflows/job-search.yml` runs the agent automatically at 8am Pakistan Time (3am UTC) on weekdays, and can also be triggered manually from the repo's **Actions** tab (**"Run workflow"** button). Since `.env`, `cv.pdf`, and `profile.json` are git-ignored and never uploaded, the workflow reads everything from **GitHub encrypted Secrets** instead (repo → Settings → Secrets and variables → Actions):

| Secret | Notes |
|---|---|
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ANTHROPIC_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` | Same values as the corresponding `.env` entries |
| `RELIEFWEB_APPNAME`, `EMAIL_TO` | Optional, same as locally |
| `PROFILE_JSON` | The full contents of your local `profile.json` file — since the CI runner has no `cv.pdf` to build one from |

`profile.py`'s `load_or_build_profile()` checks the `PROFILE_JSON` environment variable first, then falls back to a local `profile.json` file, then to rebuilding from `cv.pdf` — so the same code runs unmodified in both environments.

## Design notes

- **Source modules are interchangeable.** Every source implements the same `fetch()` contract, so the orchestration in `main.py` doesn't need to know which sources are active.
- **Structured output over free-text parsing.** Both the profile extraction and the job scoring calls use Claude's structured-output feature (a JSON schema passed to the API), so responses are guaranteed to parse — no regex or "hope the model formatted it right" logic.
- **Failures are isolated per source.** A network error, missing credential, or blocked scraper in one source prints a warning and returns an empty result set rather than crashing the whole run.
- **Remote/USA/UK filtering is per-source, not global**, because ReliefWeb's Pakistan-specific results are an intentional exception, not an oversight.
- **The ATS source matches on job title only, not description.** Full-text company job descriptions routinely mention "AI" as marketing language, which — without this constraint — matched nearly every posting at every company checked.
- **No secrets in code.** All credentials load from environment variables via `.env` locally or GitHub Secrets in CI; `.env.example` documents the required shape without real values.
