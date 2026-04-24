"""
Extractor — Stage 2 of the pipeline.

Responsibility: parse raw text into structured CVData using OpenRouter.
The raw Europass text is sent with a schema-aware prompt;
the response is parsed directly into CVData via Pydantic.

Requires: OPENROUTER_API_KEY environment variable.
Get a free key at: https://openrouter.ai/keys
"""

import json
import os
import re
from openai import OpenAI

from src.models import CVData
from src.warnings import WarningCollector

_URL_RE = re.compile(r"https?://[^\s]+")

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
    return _CLIENT


_SYSTEM_PROMPT = """\
You are a CV data extractor. You will be given the raw text of a CV (often Europass format).
Extract all information and return ONLY a valid JSON object — no explanation, no markdown fences.

The JSON must follow this exact schema:
{
  "personal": {
    "full_name": "",
    "email": "",
    "phone": "",
    "address": "",
    "linkedin": "",
    "website": "",
    "nationality": "",
    "date_of_birth": ""
  },
  "work_experience": [
    {
      "job_title": "",
      "employer": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "description": ["bullet point 1", "bullet point 2"]
    }
  ],
  "projects": [
    {
      "title": "",
      "role": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "description": ["bullet point 1", "bullet point 2"]
    }
  ],
  "education": [
    {
      "degree": "",
      "institution": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "description": ""
    }
  ],
  "extracurriculars": [
    {
      "organisation": "",
      "role": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "description": ["bullet point 1", "bullet point 2"]
    }
  ],
  "languages": [
    {"name": "", "level": ""}
  ],
  "skills": [
    {"category": "", "items": ["item1", "item2"]}
  ],
  "interests": ["interest1", "interest2"]
}

Rules:
- Use empty string "" for missing scalar fields, never null.
- Use [] for missing list fields, never null.
- For current positions use "Present" as end_date.
- Combine "Main activities and responsibilities" into description bullet points.
- Keep description bullets concise (one sentence each).
- Classify entries as work_experience if they are paid employment.
- Classify entries as projects if they are personal, academic, or open-source projects,
  or clearly labelled as projects in the CV.
- Classify entries as extracurriculars if they are volunteering, clubs, societies,
  or unpaid leadership/community roles.
- Group skills by category (e.g. "Programming", "Tools & Platforms", "Office & Documentation").
- Return the mother tongue as a language with level "Native".
- Extract interests as a flat list of short strings (e.g. ["Chess", "Open-source software"]).
- If a field is not present in the CV, omit it or use its empty default — do not invent data.
"""


def _validate_extracted(cv: CVData, warnings: WarningCollector) -> None:
    """Emit warnings for suspicious or incomplete extraction results."""
    p = cv.personal

    if not p.full_name:
        warnings.add("personal.full_name is missing.")
    if not p.email:
        warnings.add("personal.email is missing.")
    if p.email and not re.match(r"[^@]+@[^@]+\.[^@]+", p.email):
        warnings.add(f"personal.email looks malformed: '{p.email}'")
    if p.linkedin and not _URL_RE.match(p.linkedin):
        warnings.add(f"personal.linkedin does not look like a URL: '{p.linkedin}'")
    if p.website and not _URL_RE.match(p.website):
        warnings.add(f"personal.website does not look like a URL: '{p.website}'")

    # Duplicate work experience detection (same employer + start_date)
    seen_jobs: set[tuple[str, str]] = set()
    for job in cv.work_experience:
        key = (job.employer.lower().strip(), job.start_date)
        if key in seen_jobs:
            warnings.add(
                f"Duplicate work experience detected: '{job.employer}' starting '{job.start_date}'."
            )
        seen_jobs.add(key)
        if not job.description:
            warnings.add(
                f"Work experience '{job.employer} – {job.job_title}' has no description."
            )

    # Duplicate education detection
    seen_edu: set[tuple[str, str]] = set()
    for edu in cv.education:
        key = (edu.institution.lower().strip(), edu.start_date)
        if key in seen_edu:
            warnings.add(
                f"Duplicate education entry: '{edu.institution}' starting '{edu.start_date}'."
            )
        seen_edu.add(key)

    for project in cv.projects:
        if not project.description:
            warnings.add(f"Project '{project.title}' has no description.")

    for extra in cv.extracurriculars:
        if not extra.description:
            warnings.add(
                f"Extracurricular '{extra.organisation} – {extra.role}' has no description."
            )


def extract(raw_text: str, warnings: WarningCollector | None = None) -> CVData:
    """
    Turn raw CV PDF text into a structured CVData object via OpenRouter.
    Requires OPENROUTER_API_KEY to be set in the environment.
    """
    if warnings is None:
        warnings = WarningCollector()

    response = _client().chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract the CV data from this text:\n\n{raw_text}"},
        ],
    )

    raw_json = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model adds them despite instructions
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1]
        raw_json = raw_json.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON. Parse error: {e}\n\nRaw response:\n{raw_json}"
        ) from e

    cv = CVData.model_validate(data)
    _validate_extracted(cv, warnings)
    return cv
