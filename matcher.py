"""
Two-stage job matching against a candidate profile:
1. keyword_prefilter — plain Python, free, narrows a big job list down to the
   most plausible candidates by simple keyword overlap.
2. score_jobs — sends only the pre-filtered jobs to Claude, in small batches,
   to score each one 0-100 with a reason and any gaps.
"""

import json
import re

from anthropic import Anthropic

MAX_JOBS_TO_SCORE = 40
BATCH_SIZE = 10

SCORES_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "The job's index in the provided list"},
                    "score": {"type": "integer", "description": "Match score from 0 to 100"},
                    "reason": {"type": "string", "description": "One-line reason for the score"},
                    "gaps": {"type": "string", "description": "Any gaps between the candidate and this job, or empty string if none"},
                },
                "required": ["index", "score", "reason", "gaps"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["results"],
    "additionalProperties": False,
}


def _profile_keywords(profile):
    words = set()
    for field in ("skills", "target_roles"):
        for phrase in profile.get(field, []):
            words.update(re.findall(r"[a-z0-9]+", phrase.lower()))
    return words


def _job_text(job):
    return f"{job['title']} {job.get('description', '')}".lower()


def keyword_prefilter(jobs, profile, max_jobs=MAX_JOBS_TO_SCORE):
    """
    Rank jobs by how many of the profile's skill/role keywords appear in
    the job's title+description, drop non-matches, and cap the result so
    the number of jobs sent to Claude is bounded regardless of how many
    were fetched.
    """
    keywords = _profile_keywords(profile)

    scored = []
    for job in jobs:
        text = _job_text(job)
        hits = sum(1 for kw in keywords if kw in text)
        if hits > 0:
            scored.append((hits, job))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [job for _, job in scored[:max_jobs]]


def _score_batch(client, jobs, profile):
    listing = "\n".join(
        f"{i}. Title: {job['title']}\n   Company: {job['company']}\n   Location: {job['location']}\n"
        f"   Description: {job.get('description', '')[:500]}"
        for i, job in enumerate(jobs)
    )

    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=4096,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCORES_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                "Here is a candidate profile:\n" + json.dumps(profile, indent=2) +
                "\n\nScore how well each of the following jobs matches this candidate, "
                "from 0 (no fit) to 100 (excellent fit). Give one concise reason per job, "
                "and note any gaps between the candidate's background and the role "
                "(empty string if there are none.)\n\nJobs:\n" + listing
            ),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["results"]


def score_jobs(jobs, profile):
    """Score each job 0-100 against the profile, in batches, via Claude."""
    if not jobs:
        return []

    client = Anthropic()
    scored_jobs = []

    for start in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[start:start + BATCH_SIZE]
        results = _score_batch(client, batch, profile)

        for result in results:
            job = dict(batch[result["index"]])
            job["score"] = max(0, min(100, result["score"]))
            job["reason"] = result["reason"]
            job["gaps"] = result["gaps"]
            scored_jobs.append(job)

    return scored_jobs
