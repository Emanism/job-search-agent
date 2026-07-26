"""
Builds a structured profile (skills, experience, target roles, locations)
from your CV, using Claude once. The result is cached in profile.json so
we don't re-read the PDF or call the API on every run.
"""

import json
import os

from anthropic import Anthropic
from pypdf import PdfReader

CV_PATH = "cv.pdf"
PROFILE_PATH = "profile.json"

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key skills, tools, and areas of expertise",
        },
        "years_experience": {
            "type": "integer",
            "description": "Total years of relevant professional experience",
        },
        "seniority": {
            "type": "string",
            "description": "e.g. Entry-level, Mid-level, Senior, Lead, Director",
        },
        "target_roles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Job titles/role types this person is well-suited for and likely targeting",
        },
        "preferred_locations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Likely preferred work locations, including 'Remote' if applicable",
        },
    },
    "required": ["skills", "years_experience", "seniority", "target_roles", "preferred_locations"],
    "additionalProperties": False,
}


def extract_cv_text(path=CV_PATH):
    """Pull the plain text out of the CV PDF."""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def build_profile(cv_text):
    """Ask Claude to turn raw CV text into the structured profile above."""
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=2048,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": PROFILE_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                "Read this CV and extract a structured profile summarizing the "
                "candidate's skills, experience, and the kinds of roles/locations "
                "they're likely targeting.\n\nCV:\n" + cv_text
            ),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def load_or_build_profile(force_rebuild=False):
    """
    Return the cached profile from profile.json if it exists; otherwise
    extract the CV, build a fresh profile via Claude, and cache it.
    """
    if not force_rebuild and os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH) as f:
            return json.load(f)

    cv_text = extract_cv_text()
    profile = build_profile(cv_text)

    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

    return profile
