"""Extract canonical result records from raw source text.

Pure parsing/conversion only — this module never calls validation.py.
Per Step 7's requirements, extraction and validation are deliberately
separate steps: extract_records() returns candidate records (and a
separate list of lines it could not confidently parse); the caller
(CLI or tests) validates them using validation.py against
schema/result_record.schema.json.

Input format: one match per line, pipe-delimited, matching the columns
a real structured statistical-database match log exposes (see
docs/extraction.md for why this exact shape, and why no live source was
actually fetched to populate it in this step):

    date|round|venue|opponent|goals_for|goals_against

  - date: ISO 8601 'YYYY-MM-DD'
  - round: free text (e.g. 'Matchweek 12'), may be empty
  - venue: 'Home' or 'Away', relative to the team this extraction run
    is for (case-insensitive)
  - opponent: the other team's name
  - goals_for / goals_against: non-negative integers, relative to the
    team this run is for

Blank lines and lines starting with '#' are ignored. A line that
doesn't fit this shape, or has an unparseable venue/score, is never
guessed at — it's reported in ExtractionResult.ambiguous instead of
producing a record.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    records: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)  # [{"line_number", "raw_line", "reason"}]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug


def _derive_result(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if away_score > home_score:
        return "away_win"
    return "draw"


def _parse_row(raw_line: str):
    """Returns (fields_dict, None) on success or (None, reason_str) on failure."""
    parts = [p.strip() for p in raw_line.split("|")]
    if len(parts) != 6:
        return None, f"expected 6 pipe-delimited fields (date|round|venue|opponent|GF|GA), found {len(parts)}"

    date, round_, venue, opponent, gf_text, ga_text = parts

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return None, f"date {date!r} is not ISO 8601 'YYYY-MM-DD'"

    if venue.lower() not in ("home", "away"):
        return None, f"venue {venue!r} is not 'Home' or 'Away'"

    if not opponent:
        return None, "opponent is empty"

    if not re.fullmatch(r"\d+", gf_text):
        return None, f"goals_for {gf_text!r} is not a non-negative integer"
    if not re.fullmatch(r"\d+", ga_text):
        return None, f"goals_against {ga_text!r} is not a non-negative integer"

    return {
        "date": date,
        "round": round_,
        "venue": venue.lower(),
        "opponent": opponent,
        "gf": int(gf_text),
        "ga": int(ga_text),
    }, None


def extract_records(
    raw_text: str,
    *,
    sport: str,
    competition: str,
    season: str,
    team: str,
    source: str,
    source_url: str,
    source_accessed_at: str,
) -> ExtractionResult:
    """Parse raw_text (see module docstring for the line format) into
    canonical result_record dicts for `team`.

    sport/competition/season/team/source/source_url/source_accessed_at
    describe the page this content came from — they're the caller's
    context (the page's own title/URL establish them, not each row),
    not something the parser invents.

    verification_status is always 'unverified': this function performs
    no cross-source checking, by design (Step 7 doesn't implement that
    yet) — hard-coding it here (rather than accepting it as a parameter)
    is what keeps that true regardless of how this function is called.
    """
    result = ExtractionResult()

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        fields, reason = _parse_row(line)
        if fields is None:
            result.ambiguous.append({"line_number": line_number, "raw_line": raw_line, "reason": reason})
            continue

        if fields["venue"] == "home":
            home_team, away_team = team, fields["opponent"]
            home_score, away_score = fields["gf"], fields["ga"]
        else:
            home_team, away_team = fields["opponent"], team
            home_score, away_score = fields["ga"], fields["gf"]

        record = {
            "schema_version": "1.0.0",
            "event_id": (
                f"{sport}:{_slugify(competition)}:{season}:{fields['date']}:"
                f"{_slugify(home_team)}-vs-{_slugify(away_team)}"
            ),
            "sport": sport,
            "competition": competition,
            "season": season,
            "date": fields["date"],
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "result": _derive_result(home_score, away_score),
            "status": "completed",
            "source": source,
            "source_url": source_url,
            "source_accessed_at": source_accessed_at,
            "verification_status": "unverified",
            "notes": (
                f"Extracted from a {team} match log; home/away designation and score taken "
                "directly from the source's venue/goals-for/goals-against columns. Not yet "
                "cross-verified against a second source."
            ),
        }
        if fields["round"]:
            record["round"] = fields["round"]

        result.records.append(record)

    return result
