import json
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

load_dotenv()

PDFLATEX = shutil.which("pdflatex") or "/Library/TeX/texbin/pdflatex"
if not Path(PDFLATEX).exists():
    raise RuntimeError("pdflatex not found — install BasicTeX or MacTeX")

BASE_DIR = Path(__file__).parent
JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(exist_ok=True)

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index():
    return (BASE_DIR / "web" / "index.html").read_text()


@app.post("/process")
async def process(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir()

    pdf_path = job_dir / "input.pdf"
    pdf_path.write_bytes(await file.read())

    shutil.copy(BASE_DIR / "resume.cls", job_dir / "resume.cls")

    try:
        from src.cleaner import clean
        from src.extractor import extract
        from src.parser import parse_pdf
        from src.refiner import refine
        from src.renderer import render
        from src.warnings import WarningCollector

        warnings = WarningCollector()

        raw_text = parse_pdf(str(pdf_path))
        clean_text = clean(raw_text, warnings)
        cv_parsed = extract(clean_text, warnings)
        (job_dir / "parsed_cv.json").write_text(cv_parsed.model_dump_json(indent=2))

        cv_refined = refine(cv_parsed, warnings)
        (job_dir / "refined_cv.json").write_text(cv_refined.model_dump_json(indent=2))

        latex_source = render(cv_refined)
        tex_path = job_dir / "output.tex"
        tex_path.write_text(latex_source, encoding="utf-8")

        warnings.save(job_dir)

    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {e}")

    try:
        result = subprocess.run(
            [PDFLATEX, "-interaction=nonstopmode", "-output-directory", str(job_dir), str(tex_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0 and not (job_dir / "output.pdf").exists():
            raise HTTPException(500, "LaTeX compilation failed:\n" + result.stdout[-2000:])
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "LaTeX compilation timed out.")

    return {"job_id": job_id}


@app.get("/download/{job_id}/pdf")
async def download_pdf(job_id: str):
    pdf = JOBS_DIR / job_id / "output.pdf"
    if not pdf.exists():
        raise HTTPException(404, "PDF not found.")
    return FileResponse(pdf, media_type="application/pdf", filename="cv.pdf")


@app.get("/download/{job_id}/zip")
async def download_zip(job_id: str):
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, "Job not found.")

    zip_path = job_dir / "overleaf.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(job_dir / "output.tex", arcname="output.tex")
        zf.write(job_dir / "resume.cls", arcname="resume.cls")

    return FileResponse(zip_path, media_type="application/zip", filename="overleaf.zip")
