"""
Renderer — Stage 3 of the pipeline.

Responsibility: fill the LaTeX Jinja2 template with CVData
and return the final .tex string ready for Overleaf / local compilation.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.models import CVData

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# All characters that must be escaped in LaTeX body text.
# Order matters: backslash must come first so we don't double-escape.
_LATEX_ESCAPE_TABLE = [
    ("\\", r"\textbackslash{}"),
    ("&",  r"\&"),
    ("%",  r"\%"),
    ("$",  r"\$"),
    ("#",  r"\#"),
    ("_",  r"\_"),
    ("{",  r"\{"),
    ("}",  r"\}"),
    ("~",  r"\textasciitilde{}"),
    ("^",  r"\textasciicircum{}"),
]


def _escape_latex(value: str) -> str:
    """Escape special LaTeX characters in a plain-text string."""
    result = str(value)
    for char, replacement in _LATEX_ESCAPE_TABLE:
        result = result.replace(char, replacement)
    return result


def _date_range(start: str, end: str) -> str:
    """Format a start/end date pair into a compact range string."""
    if start and end:
        return f"{start} -- {end}"
    if start:
        return f"{start} -- Present"
    if end:
        return end
    return ""


def render(cv: CVData, template_name: str = "cv_template.tex.j2") -> str:
    """
    Render the CV data into a LaTeX string using the Jinja2 template.

    Args:
        cv:            populated CVData object
        template_name: filename inside the templates/ directory

    Returns:
        A string containing valid LaTeX source code.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,           # LaTeX is not HTML
        keep_trailing_newline=True,
        trim_blocks=True,           # strip newline after block tags
        lstrip_blocks=True,         # strip leading whitespace before block tags
    )

    env.filters["latex"] = _escape_latex
    env.globals["date_range"] = _date_range

    template = env.get_template(template_name)
    return template.render(cv=cv)
