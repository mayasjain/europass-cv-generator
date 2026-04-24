"""
PDF Parser — Stage 1 of the pipeline.

Responsibility: extract raw text from the Europass PDF.
Output: a plain string of the full CV text, preserving as much
        layout structure as possible for the extractor to work with.
"""

import pdfplumber


def parse_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.

    Returns the full text as a single string, with pages
    separated by a form-feed character (\f).
    """
    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                pages_text.append(text)

    return "\f".join(pages_text)


if __name__ == "__main__":
    # Quick test: run this file directly to see raw PDF output.
    # Usage: python -m src.parser
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/sample_europass.pdf"
    raw = parse_pdf(path)
    print(raw)
