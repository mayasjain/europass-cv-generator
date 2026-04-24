"""
Cleaner — Stage 1.5 of the pipeline.

Cleans raw PDF text before it is sent to the extractor.
Rules are applied in order; each operates on the full text string.
"""

from __future__ import annotations
import re
import unicodedata

from src.warnings import WarningCollector

# ---------------------------------------------------------------------------
# Unicode replacements: map common PDF artifacts to ASCII equivalents
# ---------------------------------------------------------------------------
_UNICODE_REPLACEMENTS = {
    "‘": "'",   # left single quotation mark
    "’": "'",   # right single quotation mark
    "“": '"',   # left double quotation mark
    "”": '"',   # right double quotation mark
    "–": "-",   # en dash
    "—": "-",   # em dash
    "•": "-",   # bullet
    "·": "-",   # middle dot
    "−": "-",   # minus sign
    "ﬁ": "fi",  # fi ligature
    "ﬂ": "fl",  # fl ligature
    " ": " ",   # non-breaking space
    "​": "",    # zero-width space
}

# Bullet variants to normalise to "-"
_BULLET_RE = re.compile(r"^[•‣◦⁃∙·\*\•]\s*", re.MULTILINE)

# Hyphenated line-break: word- \n word  →  wordword
_HYPHEN_LINEBREAK_RE = re.compile(r"(\w)-\n(\w)")

# Repeated whitespace (not newlines)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")

# Trailing whitespace on each line
_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)

# Date patterns → normalised MM/YYYY
_MONTH_MAP = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12",
}

_DATE_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december"
    r"|jan\.?|feb\.?|mar\.?|apr\.?|jun\.?|jul\.?|aug\.?|sep\.?|sept\.?|oct\.?|nov\.?|dec\.?)"
    r"[\s,]+(\d{4})\b",
    re.IGNORECASE,
)

# LaTeX-unsafe characters
_LATEX_UNSAFE_RE = re.compile(r"[&%$#_{}~^\\]")

# URL cleanup: strip trailing punctuation
_URL_RE = re.compile(r"https?://[^\s]+")


def _replace_unicode_artifacts(text: str) -> str:
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Normalise remaining non-ASCII to closest ASCII equivalent where possible
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    return text


def _merge_hyphenated_linebreaks(text: str) -> str:
    return _HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)


def _remove_repeated_headers_footers(text: str) -> str:
    """
    Remove lines that appear on 3 or more pages (likely headers/footers).
    Pages are separated by \f in the parser output.
    """
    pages = text.split("\f")
    if len(pages) < 3:
        return text

    # Count line frequency across pages
    line_counts: dict[str, int] = {}
    for page in pages:
        seen_on_page = set()
        for line in page.splitlines():
            stripped = line.strip()
            if stripped and len(stripped) > 2:
                if stripped not in seen_on_page:
                    line_counts[stripped] = line_counts.get(stripped, 0) + 1
                    seen_on_page.add(stripped)

    repeated = {line for line, count in line_counts.items() if count >= 3}
    if not repeated:
        return text

    cleaned_pages = []
    for page in pages:
        lines = [ln for ln in page.splitlines() if ln.strip() not in repeated]
        cleaned_pages.append("\n".join(lines))
    return "\f".join(cleaned_pages)


def _normalize_bullets(text: str) -> str:
    return _BULLET_RE.sub("- ", text)


def _normalize_whitespace(text: str) -> str:
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _TRAILING_WS_RE.sub("", text)
    return text


def _normalize_dates(text: str) -> str:
    def _replace(m: re.Match) -> str:
        month_raw = m.group(1).lower().rstrip(".")
        year = m.group(2)
        month_num = _MONTH_MAP.get(month_raw, "")
        return f"{month_num}/{year}" if month_num else m.group(0)
    return _DATE_RE.sub(_replace, text)


def _normalize_urls(text: str) -> str:
    def _fix_url(m: re.Match) -> str:
        url = m.group(0).rstrip(".,;:)'\"")
        if not url.startswith("https://") and not url.startswith("http://"):
            url = "https://" + url
        return url
    return _URL_RE.sub(_fix_url, text)


def _warn_latex_unsafe(text: str, warnings: WarningCollector) -> None:
    """Warn about characters that need escaping at render time — do not strip."""
    matches = _LATEX_UNSAFE_RE.findall(text)
    if matches:
        unique = sorted(set(matches))
        warnings.add(
            f"LaTeX-unsafe characters found in raw text (will be escaped at render): "
            f"{unique}"
        )


def clean(raw_text: str, warnings: WarningCollector) -> str:
    """
    Apply all cleaning rules to raw PDF text in order.
    Returns cleaned text. Warnings are emitted via the collector.
    """
    text = raw_text

    # 1. Unicode artifact cleanup (must be first — normalises encoding)
    text = _replace_unicode_artifacts(text)

    # 2. Hyphenated line-break merge
    text = _merge_hyphenated_linebreaks(text)

    # 3. Repeated header/footer removal
    text = _remove_repeated_headers_footers(text)

    # 4. Bullet normalisation
    text = _normalize_bullets(text)

    # 5. Whitespace normalisation
    text = _normalize_whitespace(text)

    # 6. Date normalisation
    text = _normalize_dates(text)

    # 7. URL normalisation
    text = _normalize_urls(text)

    # 8. LaTeX character flagging (warn only — escaping happens in renderer)
    _warn_latex_unsafe(text, warnings)

    # Note: skill list splitting happens in the extractor via LLM prompt rules.

    return text
