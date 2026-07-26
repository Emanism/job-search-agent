# Job-Search Agent

A small Python agent that pulls job listings from multiple sources, deduplicates them, ranks them against a candidate's CV using Claude, and emails a summary of the best matches — without sending every fetched job to an LLM.

## What it does

1. **Fetches** jobs from multiple sources in parallel role searches (currently Adzuna and ReliefWeb; see [Architecture](#architecture)).
2. **Deduplicates** the combined results by posting URL.
3. **Builds a candidate profile** from a CV (PDF) once, via Claude, and caches it — skills, seniority, target roles, preferred locations.
4. **Pre-filters** the job list against that profile using plain keyword overlap — no API calls.
5. **Scores** only the surviving candidates with Claude (0–100, with a one-line reason and any gaps), batched to minimize requests.
6. **Prints** results sorted best-match-first.
7. **Emails** a summary of jobs scoring at or above a configurable threshold — nothing is sent if no job clears it.

## Architecture

```
                ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                │    Adzuna    │   │   ReliefWeb  │   │  Greenhouse/  │
                │  (mainstream)│   │ (dev sector) │   │ Lever (stub) │
                └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
                       │                  │                  │
                       └────────┬─────────┴─────────┬────────┘
                                 ▼                   
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

Each job source is an independent module exposing a single `fetch()` function that returns a common shape (`title`, `company`, `location`, `link`, `description`, `source`). Adding a new source is a matter of writing one new module with that interface — no changes required elsewhere. A Greenhouse/Lever module is stubbed out and ready to implement (both platforms expose free, per-company JSON job-board APIs).

### Two-stage matching: why costs stay bounded

Sending every fetched job's description to an LLM for scoring doesn't scale — cost grows linearly with how many jobs your sources happen to return, which is fully outside your control. This project splits matching into two stages instead:

- **Stage 1 — keyword pre-filter (free).** The candidate profile's skills and target roles are reduced to a keyword set; every fetched job is scored by simple keyword overlap in plain Python. Zero-overlap jobs are dropped, and the survivors are capped at a fixed ceiling before anything reaches the LLM.
- **Stage 2 — Claude scoring (paid, but bounded).** Only the capped, pre-filtered candidate set is sent to Claude, in batches (10 jobs per request, not one request per job) using structured output (a JSON schema), so parsing is exact and there's no free-text cleanup step.

The result: however many jobs the sources return — 80 today, potentially hundreds later — the number of jobs actually scored by Claude, and therefore the API spend per run, stays capped by a single constant.

The CV → candidate-profile extraction is a **one-time** Claude call, cached to disk (`profile.json`). It's only repeated if the cache is deleted or a rebuild is explicitly requested — normal runs don't touch the CV or the LLM for profile building at all.

### Email delivery

After scoring, jobs at or above a configurable threshold (`SCORE_THRESHOLD` in `main.py`, default 40) are emailed via Gmail's SMTP server, sorted best-first with score, title, company, location, reason, gaps, and apply link. If nothing clears the threshold, no email is sent — the run stays silent rather than delivering an empty message. Delivery uses a Gmail **app password** (a revocable, purpose-specific credential — not the account's real password), read from the environment alongside the other credentials.

## Project structure

```
main.py               orchestrates: build/load profile → fetch → dedupe → pre-filter → score → print → email
profile.py            extracts CV text (PDF) and builds/caches the structured candidate profile
matcher.py            keyword pre-filter + batched Claude scoring
mailer.py             emails jobs scoring >= threshold via Gmail; sends nothing if none qualify
sources/
  adzuna.py           Adzuna job board (multi-country, keyword-based remote search)
  reliefweb.py        ReliefWeb (UN / development-sector jobs)
  greenhouse.py        stub for Greenhouse/Lever company career pages
requirements.txt      pinned dependencies
.env.example          template for required environment variables
```

## Setup

Requires Python 3.10+.

```bash
git clone <this-repo>
cd job-agent

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

Any source (or the mailer) missing its credentials is skipped with a warning — the agent still runs on whatever's configured, rather than failing outright.

### Email setup

Email delivery uses Gmail's SMTP server with an **app password**, not the account's normal password:

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

Output is printed to stdout, sorted best-match-first, each entry showing score, title, company, location, match reason, gaps, and link. If Gmail credentials are configured, the jobs at or above `SCORE_THRESHOLD` are also emailed in the same format; nothing is sent if none qualify.

## Design notes

- **Source modules are interchangeable.** Every source implements the same `fetch()` contract, so the orchestration in `main.py` doesn't need to know which sources are active.
- **Structured output over free-text parsing.** Both the profile extraction and the job scoring calls use Claude's structured-output feature (a JSON schema passed to the API), so responses are guaranteed to parse — no regex or "hope the model formatted it right" logic.
- **Failures are isolated per source.** A network error or missing credential in one source prints a warning and returns an empty result set rather than crashing the whole run.
- **No secrets in code.** All credentials load from environment variables via `.env` (git-ignored); `.env.example` documents the required shape without real values.
