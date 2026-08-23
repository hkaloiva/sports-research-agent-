"""EventResult: the sport-generic canonical record (schema/event_result.schema.json).

Generalizes result_record.schema.json's football-only home_team/away_team/
home_score/away_score into N `participants`, each with an optional
`score` and/or `placement` — the same shape covers team sports,
individual sports, and motorsport. See docs/data-model.md.
"""

import re


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def derive_two_participant_result(participants: list) -> str:
    """For exactly two participants with roles 'home'/'away' and numeric
    scores, derive home_win/away_win/draw. Raises ValueError otherwise —
    callers should only call this in that specific shape; other shapes
    (individual/motorsport) should set `result` themselves, or leave it
    null and rely on participants[].placement instead."""
    by_role = {p["role"]: p for p in participants if p.get("role") in ("home", "away")}
    if set(by_role) != {"home", "away"}:
        raise ValueError("derive_two_participant_result requires exactly one 'home' and one 'away' participant")
    home_score, away_score = by_role["home"].get("score"), by_role["away"].get("score")
    if not isinstance(home_score, (int, float)) or not isinstance(away_score, (int, float)):
        raise ValueError("both participants must have a numeric score to derive a result")
    if home_score > away_score:
        return "home_win"
    if away_score > home_score:
        return "away_win"
    return "draw"


def build_two_participant_event_id(sport: str, competition: str, season: str, date: str, home_name: str, away_name: str) -> str:
    return f"{sport}:{slugify(competition)}:{season}:{date}:{slugify(home_name)}-vs-{slugify(away_name)}"


def build_named_event_id(sport: str, competition: str, season: str, date: str, event_name: str) -> str:
    return f"{sport}:{slugify(competition)}:{season}:{date}:{slugify(event_name)}"


def make_event_result(
    *,
    sport: str,
    competition: str,
    season: str,
    date: str,
    participants: list,
    status: str,
    source: str,
    source_url: str,
    source_accessed_at: str,
    verification_status: str = "unverified",
    event_id: str = None,
    event_name: str = None,
    round: str = None,  # noqa: A002 - matches schema field name
    location: dict = None,
    result: str = None,
    notes: str = None,
) -> dict:
    """Build an EventResult dict. Does not validate — see
    sports_research/validation/schema_validation.py for that, kept as a
    deliberately separate step (same pattern as Step 7's extractor.py)."""
    if event_id is None:
        if len(participants) == 2 and {p.get("role") for p in participants} == {"home", "away"}:
            by_role = {p["role"]: p for p in participants}
            event_id = build_two_participant_event_id(sport, competition, season, date, by_role["home"]["name"], by_role["away"]["name"])
        elif event_name:
            event_id = build_named_event_id(sport, competition, season, date, event_name)
        else:
            names = "-".join(slugify(p["name"]) for p in participants)
            event_id = f"{sport}:{slugify(competition)}:{season}:{date}:{names}"

    record = {
        "schema_version": "1.0.0",
        "event_id": event_id,
        "sport": sport,
        "competition": competition,
        "season": season,
        "date": date,
        "participants": participants,
        "status": status,
        "result": result,
        "source": source,
        "source_url": source_url,
        "source_accessed_at": source_accessed_at,
        "verification_status": verification_status,
    }
    if event_name:
        record["event_name"] = event_name
    if round:
        record["round"] = round
    if location:
        record["location"] = location
    if notes:
        record["notes"] = notes
    return record
