"""
Refiner — Stage 3 of the pipeline (between extraction and rendering).

Rewrites descriptive/narrative content professionally using an LLM.
Factual fields (names, titles, dates, locations, links) are never touched.
"""

from __future__ import annotations
import json
import os

from openai import OpenAI

from src.models import CVData, WorkExperience, Project, Extracurricular
from src.warnings import WarningCollector

_CLIENT = None


def _client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
    return _CLIENT


_SYSTEM_PROMPT = """\
You are a professional CV editor. You will receive a JSON array of bullet-point strings
from a CV. Rewrite each bullet to sound polished, confident, and concise — suitable for
a graduate or professional CV targeting competitive employers.

Rules:
- Return ONLY a valid JSON array of strings, one per input bullet. No explanation, no markdown.
- Preserve the exact number of bullets (one output per input, in the same order).
- Do NOT change any facts: numbers, technologies, company names, outcomes, dates.
- Do NOT invent new information or expand scope.
- Use strong action verbs. Remove filler phrases ("responsible for", "helped with", "involved in").
- Each bullet should be one concise sentence.
- If a bullet is already well-written, return it unchanged.
"""


def _rewrite_bullets(bullets: list[str]) -> list[str]:
    """Send a list of bullets to the LLM and return the rewritten list."""
    if not bullets:
        return bullets

    response = _client().chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(bullets)},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if model adds them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Refiner LLM returned invalid JSON. Error: {e}\n\nRaw:\n{raw}"
        ) from e

    if not isinstance(result, list) or len(result) != len(bullets):
        raise ValueError(
            f"Refiner returned {len(result)} bullets for {len(bullets)} inputs."
        )

    return [str(b) for b in result]


def refine(cv: CVData, warnings: WarningCollector) -> CVData:
    """
    Return a new CVData with descriptive bullet points professionally rewritten.
    All factual fields are copied unchanged.
    """
    data = cv.model_dump()

    # Work experience
    for i, job in enumerate(data["work_experience"]):
        original = job["description"]
        if not original:
            warnings.add(
                f"Work experience '{job['employer']} – {job['job_title']}' "
                f"has no description bullets to refine."
            )
            continue
        data["work_experience"][i]["description"] = _rewrite_bullets(original)

    # Projects
    for i, project in enumerate(data["projects"]):
        original = project["description"]
        if not original:
            warnings.add(f"Project '{project['title']}' has no description bullets to refine.")
            continue
        data["projects"][i]["description"] = _rewrite_bullets(original)

    # Extracurriculars
    for i, extra in enumerate(data["extracurriculars"]):
        original = extra["description"]
        if not original:
            warnings.add(
                f"Extracurricular '{extra['organisation']} – {extra['role']}' "
                f"has no description bullets to refine."
            )
            continue
        data["extracurriculars"][i]["description"] = _rewrite_bullets(original)

    return CVData.model_validate(data)
