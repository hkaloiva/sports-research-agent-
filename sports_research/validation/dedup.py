"""Event-level duplicate detection.

Distinct from search.py's URL-level dedup (Step 6) — this looks at
whether two EventResults, possibly from different sources with different
event_ids, describe the same real-world event.
"""


def _participant_name_set(event: dict) -> frozenset:
    return frozenset(p["name"].strip().lower() for p in event.get("participants", []))


def event_signature(event: dict) -> tuple:
    """Two events with the same signature are considered the same
    real-world event. Deliberately coarse (sport+competition+date+
    participant names) rather than trying to fuzzy-match team-name
    spelling variants, which would risk merging genuinely different
    events."""
    return (event.get("sport"), event.get("competition"), event.get("date"), _participant_name_set(event))


def group_duplicate_events(events: list) -> list:
    """Returns a list of groups; each group is a list of indices into
    `events` sharing the same signature. Groups of size 1 are not
    duplicates and are omitted."""
    groups = {}
    for i, event in enumerate(events):
        groups.setdefault(event_signature(event), []).append(i)
    return [indices for indices in groups.values() if len(indices) > 1]
