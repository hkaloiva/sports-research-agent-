"""CSV export via pandas.

EventResult's `participants` array varies in length by sport (2 for a
team match, N for a placement-based event), so CSV uses one row per
(event, participant) pair — the standard, lossless way to flatten a
one-to-many relationship into a flat table, and it works uniformly for
every sport rather than assuming exactly two participants.
"""

import pandas as pd


def _rows_for_event(event: dict):
    base = {
        "event_id": event["event_id"],
        "sport": event["sport"],
        "competition": event["competition"],
        "season": event["season"],
        "event_name": event.get("event_name"),
        "date": event["date"],
        "round": event.get("round"),
        "status": event["status"],
        "result": event.get("result"),
        "source": event["source"],
        "source_url": event["source_url"],
        "source_accessed_at": event["source_accessed_at"],
        "verification_status": event["verification_status"],
        "notes": event.get("notes"),
    }
    for participant in event["participants"]:
        row = dict(base)
        row["participant_name"] = participant["name"]
        row["participant_role"] = participant["role"]
        row["participant_score"] = participant.get("score")
        row["participant_placement"] = participant.get("placement")
        yield row


def export_csv(records: list, path) -> None:
    rows = [row for event in records for row in _rows_for_event(event)]
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
