"""
Starter list of companies to check via sources/ats.py, each with the
applicant-tracking system (ATS) they publish a free public job board on.
Verified live before adding (see conversation history / commit messages).

Add more any time: pick a company, guess its board slug (usually the
company's name, lowercase, no spaces), and test it directly, e.g.:
  Greenhouse: https://boards-api.greenhouse.io/v1/boards/<slug>/jobs
  Lever:      https://api.lever.co/v0/postings/<slug>?mode=json
  Ashby:      https://api.ashbyhq.com/posting-api/job-board/<slug>
A 200 response with a non-empty job list means the slug is right.
"""

COMPANIES = [
    {"name": "GitLab", "ats": "greenhouse", "slug": "gitlab"},
    {"name": "Elastic", "ats": "greenhouse", "slug": "elastic"},
    {"name": "Figma", "ats": "greenhouse", "slug": "figma"},
    {"name": "Webflow", "ats": "greenhouse", "slug": "webflow"},
    {"name": "Asana", "ats": "greenhouse", "slug": "asana"},
    {"name": "Coinbase", "ats": "greenhouse", "slug": "coinbase"},
    {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
    {"name": "Twilio", "ats": "greenhouse", "slug": "twilio"},
    {"name": "Dropbox", "ats": "greenhouse", "slug": "dropbox"},
    {"name": "Squarespace", "ats": "greenhouse", "slug": "squarespace"},
    {"name": "Anthropic", "ats": "greenhouse", "slug": "anthropic"},
    {"name": "Palantir", "ats": "lever", "slug": "palantir"},
    {"name": "ElevenLabs", "ats": "ashby", "slug": "elevenlabs"},
    {"name": "Ramp", "ats": "ashby", "slug": "ramp"},
    {"name": "Linear", "ats": "ashby", "slug": "linear"},
    {"name": "Vercel", "ats": "ashby", "slug": "vercel"},
    {"name": "Notion", "ats": "ashby", "slug": "notion"},
    {"name": "OpenAI", "ats": "ashby", "slug": "openai"},
]
