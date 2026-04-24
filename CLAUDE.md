# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Requires `OPENROUTER_API_KEY` in `.env` (used by `src/extractor.py` to call `google/gemini-2.0-flash-001` via OpenRouter).

## Running

```bash
# Full pipeline (PDF → JSON → refined JSON → .tex)
python main.py samples/CV\ 1.pdf

# Re-render .tex from edited JSON (skips all LLM calls)
python main.py --from-json output/run_YYYY_MM_DD_HHMM/refined_cv.json

# Inspect raw PDF text (debug stage 1)
python -m src.parser "samples/CV 1.pdf"
```

Each run writes all artifacts to a timestamped folder:
```
output/run_YYYY_MM_DD_HHMM/
  parsed_cv.json    ← after extraction
  refined_cv.json   ← after LLM rewrite
  output.tex
  warnings.log
```

## Architecture

Five sequential stages:

1. **`src/parser.py`** — Extracts raw text from the PDF with `pdfplumber` (pages joined by `\f`).
2. **`src/cleaner.py`** — Cleans raw text before extraction: unicode normalization, hyphenated line-break merging, repeated header/footer removal, bullet normalization, whitespace, date normalization (`January 2020` → `01/2020`), URL normalization, and LaTeX-unsafe character warnings.
3. **`src/extractor.py`** — Sends cleaned text to `google/gemini-2.0-flash-001` via OpenRouter with a schema-aware system prompt. Returns a validated `CVData`. Accepts a `WarningCollector` and emits warnings for missing fields, empty descriptions, duplicate entries, and malformed URLs.
4. **`src/refiner.py`** — Sends only description bullet arrays (work, projects, extracurriculars) to the LLM for professional rewriting. Factual fields (names, titles, dates, locations) are never touched.
5. **`src/renderer.py`** — Fills `templates/cv_template.tex.j2` (Jinja2) with `CVData`. Always apply `|latex` filter to user strings; use `date_range(start, end)` global for date pairs.

`src/models.py` defines `CVData` (root) with: `personal`, `work_experience`, `projects`, `education`, `extracurriculars`, `languages`, `skills`, `interests`.

`src/warnings.py` — `WarningCollector` is passed through all stages, accumulates warnings, prints them live, and saves `warnings.log` at the end.

### Template & LaTeX class

- `templates/cv_template.tex.j2` — Jinja2 template; `|latex` filter escapes LaTeX special characters.
- `resume.cls` — provides `rSection` and `rSubsection` environments. `rSubsection` takes 4 args: `{employer}{date}{title}{location}`.

Sample PDFs are in `samples/`.
