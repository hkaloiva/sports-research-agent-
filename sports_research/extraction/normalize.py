"""Normalization helpers used during extraction: dates, names, scores."""

import re
from datetime import datetime

_MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["", "January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"],
        start=0,
    )
    if m
}

_DATE_PATTERNS = [
    (r"(\d{4})-(\d{2})-(\d{2})", lambda m: (int(m[1]), int(m[2]), int(m[3]))),  # ISO
    (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: (int(m[3]), int(m[2]), int(m[1]))),  # DD/MM/YYYY
]


def normalize_date(text: str):
    """Best-effort: return an ISO 'YYYY-MM-DD' string, or None if the text
    doesn't confidently parse as a date. Never guesses a date from
    surrounding context — only from digits/month-names actually present
    in `text`."""
    text = text.strip()

    for pattern, extractor in _DATE_PATTERNS:
        match = re.fullmatch(pattern, text)
        if match:
            year, month, day = extractor(match)
            try:
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                return None

    match = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if match:
        day, month_name, year = match.groups()
        month = _MONTHS.get(month_name.lower())
        if month:
            try:
                return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
            except ValueError:
                return None

    match = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", text)
    if match:
        month_name, day, year = match.groups()
        month = _MONTHS.get(month_name.lower())
        if month:
            try:
                return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
            except ValueError:
                return None

    return None


def normalize_name(text: str) -> str:
    """Collapse whitespace, strip footnote markers like '[1]' and stray
    punctuation at the edges. Never changes the substantive spelling of a
    name — that would risk misidentifying who actually played."""
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,-")


def normalize_score(text: str):
    """Parse a single integer score token, or None if it doesn't
    confidently parse. Never rounds, truncates, or guesses."""
    text = text.strip()
    if re.fullmatch(r"\d+", text):
        return int(text)
    return None
