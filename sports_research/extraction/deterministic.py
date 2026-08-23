"""DeterministicExtractor: pattern-based extraction from real page text.

Two tractable, documented patterns (see docs/extraction.md for the honest
scope/limitations of pattern-based extraction from arbitrary web text):

1. Two-participant score lines: "Team A 2-1 Team B" (also en/em dash),
   generalizing beyond football to any two-participant sport with a
   numeric score each side, with an optional nearby date.
2. Placement/leaderboard lines: "1. Name", "1) Name", "1st Name" — for
   individual/motorsport events where the result is a ranked list of
   competitors, not a two-side score.

Never invents a value: a line that doesn't confidently match a pattern
is skipped and reported in ExtractionResult.ambiguous rather than guessed
at. This is the baseline extractor — see local_llm.py for the optional,
local-only extension point for harder pages.
"""

import re
from dataclasses import dataclass, field

from sports_research.models.event_result import make_event_result
from .normalize import normalize_date, normalize_name, normalize_score

_SCORE_LINE = re.compile(
    r"^(?P<name1>.+?)\s+(?P<score1>\d+)\s*[-–—:]\s*(?P<score2>\d+)\s+(?P<name2>.+?)$"
)
_DATE_LINE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[:\-]?\s*$"
)
_PLACEMENT_LINE = re.compile(
    r"^\s*(?P<placement>\d+)(?:st|nd|rd|th)?[.\)]\s+(?P<name>.+?)(?:\s+[-–—:]\s*(?P<score>[\d.]+))?\s*$"
)


@dataclass
class ExtractionResult:
    records: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)  # [{"line_number", "raw_line", "reason"}]


def extract_two_participant_events(
    text: str,
    *,
    sport: str,
    competition: str,
    season: str,
    source: str,
    source_url: str,
    source_accessed_at: str,
) -> ExtractionResult:
    """Scans `text` line by line for '<name> <score>-<score> <name>' lines,
    carrying forward the most recently seen date line as each match's date
    until a new date line appears. A score line with no date seen yet is
    reported as ambiguous rather than guessed."""
    result = ExtractionResult()
    current_date = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        date_match = _DATE_LINE.match(line)
        if date_match:
            parsed = normalize_date(date_match.group("date"))
            if parsed:
                current_date = parsed
            continue

        score_match = _SCORE_LINE.match(line)
        if not score_match:
            continue

        name1 = normalize_name(score_match.group("name1"))
        name2 = normalize_name(score_match.group("name2"))
        score1 = normalize_score(score_match.group("score1"))
        score2 = normalize_score(score_match.group("score2"))

        if not name1 or not name2:
            result.ambiguous.append({"line_number": line_number, "raw_line": raw_line, "reason": "could not identify two participant names"})
            continue
        if score1 is None or score2 is None:
            result.ambiguous.append({"line_number": line_number, "raw_line": raw_line, "reason": "score did not parse as two integers"})
            continue
        if current_date is None:
            result.ambiguous.append({"line_number": line_number, "raw_line": raw_line, "reason": "no date established yet for this line"})
            continue

        participants = [
            {"name": name1, "role": "home", "score": score1},
            {"name": name2, "role": "away", "score": score2},
        ]
        result.records.append(make_event_result(
            sport=sport, competition=competition, season=season, date=current_date,
            participants=participants, status="completed",
            result="home_win" if score1 > score2 else ("away_win" if score2 > score1 else "draw"),
            source=source, source_url=source_url, source_accessed_at=source_accessed_at,
            notes="Extracted from unstructured source text via deterministic score-line pattern matching; not yet cross-verified against a second source.",
        ))

    return result


def extract_placement_event(
    text: str,
    *,
    sport: str,
    competition: str,
    season: str,
    event_name: str,
    date: str,
    source: str,
    source_url: str,
    source_accessed_at: str,
) -> ExtractionResult:
    """Scans `text` for ranked-list lines ('1. Name', '2) Name', ...) and
    builds ONE event whose participants carry each competitor's placement
    (and score, if a trailing number was present). date must be supplied
    by the caller (a page rarely repeats the event date on every
    leaderboard row) — this function never invents one."""
    result = ExtractionResult()
    participants = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = _PLACEMENT_LINE.match(line)
        if not match:
            continue

        name = normalize_name(match.group("name"))
        if not name:
            result.ambiguous.append({"line_number": line_number, "raw_line": raw_line, "reason": "could not identify a competitor name"})
            continue

        placement = int(match.group("placement"))
        score_text = match.group("score")
        entry = {"name": name, "role": "competitor", "placement": placement}
        if score_text is not None:
            try:
                entry["score"] = float(score_text) if "." in score_text else int(score_text)
            except ValueError:
                pass
        participants.append(entry)

    if not participants:
        return result

    result.records.append(make_event_result(
        sport=sport, competition=competition, season=season, date=date,
        participants=participants, status="completed",
        result="win" if any(p["placement"] == 1 for p in participants) else None,
        event_name=event_name,
        source=source, source_url=source_url, source_accessed_at=source_accessed_at,
        notes="Extracted from unstructured source text via deterministic placement-list pattern matching; not yet cross-verified against a second source.",
    ))
    return result
