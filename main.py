"""
Europass CV Generator — entry point.

Full pipeline:
  PDF → parser → cleaner → extractor → [parsed_cv.json]
                                              ↓
                                          refiner → [refined_cv.json]
                                                         ↓
                                                     renderer → output.tex
                                                          + warnings.log

Re-render from JSON (skips LLM calls):
  python main.py --from-json output/run_XXXX/refined_cv.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from src.parser import parse_pdf
from src.cleaner import clean
from src.extractor import extract
from src.refiner import refine
from src.renderer import render
from src.models import CVData
from src.warnings import WarningCollector


def _make_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y_%m_%d_%H%M")
    run_dir = Path("output") / f"run_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_full(pdf_path: str) -> None:
    """Full pipeline: PDF → parsed JSON → refined JSON → .tex"""
    run_dir = _make_run_dir()
    warnings = WarningCollector()

    print(f"Output folder: {run_dir}\n")

    print("[1/5] Parsing PDF...")
    raw_text = parse_pdf(pdf_path)

    print("[2/5] Cleaning extracted text...")
    clean_text = clean(raw_text, warnings)

    print("[3/5] Extracting structured data via LLM...")
    cv_parsed = extract(clean_text, warnings)

    parsed_json_path = run_dir / "parsed_cv.json"
    parsed_json_path.write_text(
        cv_parsed.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"  Saved: {parsed_json_path}")

    print("[4/5] Refining content via LLM...")
    cv_refined = refine(cv_parsed, warnings)

    refined_json_path = run_dir / "refined_cv.json"
    refined_json_path.write_text(
        cv_refined.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"  Saved: {refined_json_path}")

    print("[5/5] Rendering LaTeX...")
    latex_output = render(cv_refined)

    tex_path = run_dir / "output.tex"
    tex_path.write_text(latex_output, encoding="utf-8")
    print(f"  Saved: {tex_path}")

    warnings.save(run_dir)
    print(f"\nDone. {len(warnings)} warning(s). All outputs in: {run_dir}")


def run_from_json(json_path: str) -> None:
    """
    Re-render a .tex from an existing parsed_cv.json or refined_cv.json.
    Skips all LLM calls — useful for tweaking JSON and regenerating output.
    """
    path = Path(json_path)
    if not path.exists():
        print(f"Error: file not found: {json_path}")
        sys.exit(1)

    run_dir = path.parent
    warnings = WarningCollector()

    print(f"[1/1] Rendering LaTeX from: {path.name}...")
    data = json.loads(path.read_text(encoding="utf-8"))
    cv = CVData.model_validate(data)

    latex_output = render(cv)
    tex_path = run_dir / "output.tex"
    tex_path.write_text(latex_output, encoding="utf-8")
    print(f"  Saved: {tex_path}")

    warnings.save(run_dir)
    print(f"\nDone. LaTeX written to: {tex_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a Europass CV PDF to a LaTeX CV."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("pdf", nargs="?", help="Path to the Europass PDF")
    group.add_argument(
        "--from-json",
        metavar="JSON_PATH",
        help="Re-render .tex from an existing parsed_cv.json or refined_cv.json",
    )

    args = parser.parse_args()

    if args.from_json:
        run_from_json(args.from_json)
    else:
        run_full(args.pdf)
