"""Cross-source verification classification.

Never marks a record VERIFIED merely because one source produced it —
that requires at least two independent (different-domain) sources that
agree. When they disagree, both claims are preserved, not overwritten.
"""

HIGH_TRUST_SOURCE_TYPES = {"official_competition_source", "official_club_source", "statistical_database"}


def _agree(event_a: dict, event_b: dict) -> bool:
    """Two events (already known to share a signature — see dedup.py)
    'agree' if every participant's score and every participant's
    placement match, and the top-level result matches."""
    if event_a.get("result") != event_b.get("result"):
        return False
    by_name_a = {p["name"].strip().lower(): p for p in event_a.get("participants", [])}
    by_name_b = {p["name"].strip().lower(): p for p in event_b.get("participants", [])}
    if set(by_name_a) != set(by_name_b):
        return False
    for name, pa in by_name_a.items():
        pb = by_name_b[name]
        if pa.get("score") != pb.get("score") or pa.get("placement") != pb.get("placement"):
            return False
    return True


def classify_group(events: list, domains: list) -> dict:
    """events: EventResult dicts sharing the same signature (see dedup.py).
    domains: parallel list of the domain each event's source_url came from.

    Returns {"verification_status": ..., "agreeing_indices": [...],
    "disagreeing_indices": [...]} — never claims VERIFIED from a single
    source, and on disagreement lists every index involved rather than
    silently picking one.
    """
    distinct_domains = set(domains)

    if len(events) == 1:
        status = "unverified"
        return {"verification_status": status, "agreeing_indices": [0], "disagreeing_indices": []}

    reference = events[0]
    agreeing, disagreeing = [], []
    for i, event in enumerate(events):
        (agreeing if _agree(reference, event) else disagreeing).append(i)

    if disagreeing:
        return {"verification_status": "conflicting", "agreeing_indices": agreeing, "disagreeing_indices": disagreeing}

    if len(distinct_domains) >= 2:
        return {"verification_status": "verified", "agreeing_indices": agreeing, "disagreeing_indices": []}

    # Same domain reporting the same thing more than once (e.g. two pages
    # on the same site) isn't independent corroboration.
    return {"verification_status": "unverified", "agreeing_indices": agreeing, "disagreeing_indices": []}
