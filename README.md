# Europass CV Generator

Convert a Europass CV PDF into a polished, professional CV — download as a compiled PDF or edit on Overleaf.

## How it works

Upload your Europass CV PDF through the web interface. A 5-stage pipeline processes it:

1. **Parse** — extracts raw text from the PDF
2. **Clean** — normalises unicode, dates, bullets, and whitespace
3. **Extract** — sends cleaned text to Google Gemini (via OpenRouter) and returns structured CV data
4. **Refine** — rewrites description bullets professionally using the LLM (factual fields like names, dates, and locations are never touched)
5. **Render** — fills a Jinja2 LaTeX template and compiles to PDF

You get back a compiled PDF and a ZIP ready to upload directly to Overleaf.

## Setup

**Requirements:** Python 3.10+, and [BasicTeX](https://www.tug.org/mactex/morepackages.html) or MacTeX for PDF compilation.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your OpenRouter API key:

```
OPENROUTER_API_KEY=your_key_here
```

Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys). The pipeline uses `google/gemini-2.0-flash-001`.

## Running the web app

```bash
source .venv/bin/activate
uvicorn app:app --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Running the CLI

```bash
# Full pipeline
python main.py "samples/CV 1.pdf"

# Re-render from existing JSON (skips LLM calls)
python main.py --from-json output/run_YYYY_MM_DD_HHMM/refined_cv.json

# Inspect raw extracted text
python -m src.parser "samples/CV 1.pdf"
```

Each run saves all artifacts to a timestamped folder:

```
output/run_YYYY_MM_DD_HHMM/
  parsed_cv.json    ← raw LLM extraction
  refined_cv.json   ← rewritten bullets
  output.tex        ← LaTeX source
  warnings.log
```

## Project structure

```
app.py                  ← FastAPI web app
main.py                 ← CLI entry point
resume.cls              ← Custom LaTeX document class
templates/
  cv_template.tex.j2    ← Jinja2 LaTeX template
src/
  parser.py             ← PDF → raw text
  cleaner.py            ← text normalisation
  extractor.py          ← LLM structured extraction
  refiner.py            ← LLM bullet rewriting
  renderer.py           ← LaTeX rendering
  models.py             ← Pydantic data models
  warnings.py           ← Warning collector
web/
  index.html            ← Single-page frontend
```
