"""Human-readable research report — a plain-text summary of a
ResearchOutcome, clearly stating sources, verification, uncertainties,
and missing data. Never claims completeness the pipeline hasn't earned —
see docs/limitations.md."""


def render_report(outcome) -> str:
    lines = []
    lines.append("SPORTS RESEARCH AGENT — RESEARCH REPORT")
    lines.append("=" * 40)

    if outcome.request:
        lines.append(f"Request: {outcome.request.get('raw_query')}")
        lines.append(f"Status: {outcome.request.get('status')}")

    if outcome.clarification_needed:
        lines.append("")
        lines.append("This request needs clarification before it can be researched:")
        for c in outcome.clarification_questions:
            lines.append(f"  - {c['field']}: {c['question']} ({c['reason']})")
        return "\n".join(lines)

    if outcome.error:
        lines.append(f"Error: {outcome.error}")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"Queries executed: {len(outcome.plan['search_queries']) if outcome.plan else 0}")
    for q in (outcome.plan["search_queries"] if outcome.plan else []):
        lines.append(f"  - {q['query']}")

    lines.append("")
    lines.append(f"Sources found via search: {len(outcome.search_execution['results']) if outcome.search_execution else 0}")
    lines.append(f"Sources retrieved: {len([s for s in outcome.sources if s['retrieval_status'] == 'ok'])} of {len(outcome.sources)} attempted")
    for s in outcome.sources:
        status = "OK" if s["retrieval_status"] == "ok" else f"FAILED ({s['retrieval_status']})"
        lines.append(f"  - [{status}] {s['title']} ({s['url']}) [{s['source_type']}]")

    lines.append("")
    lines.append(f"Records extracted: {len(outcome.records)}")

    verified = [r for r in outcome.records if r.get("verification_status") == "verified"]
    conflicting = [r for r in outcome.records if r.get("verification_status") == "conflicting"]
    unverified = [r for r in outcome.records if r.get("verification_status") == "unverified"]
    lines.append(f"  Verified (2+ independent sources agree): {len(verified)}")
    lines.append(f"  Unverified (single source only): {len(unverified)}")
    lines.append(f"  Conflicting (sources disagree): {len(conflicting)}")

    if conflicting:
        lines.append("")
        lines.append("CONFLICTS — sources disagree on these events, neither claim was overwritten:")
        for r in conflicting:
            lines.append(f"  - {r['event_id']}: {r['source']} says {[p.get('score') for p in r['participants']]}")

    if outcome.validation_problems:
        lines.append("")
        lines.append(f"Validation issues found in {len(outcome.validation_problems)} record(s):")
        for event_id, problems in outcome.validation_problems.items():
            for problem in problems:
                lines.append(f"  - {event_id}: {problem}")

    if outcome.completeness:
        c = outcome.completeness
        lines.append("")
        lines.append("Completeness:")
        lines.append(f"  Expected: {c['expected'] if c['expected'] is not None else 'unknown (no documented rule for this competition)'}")
        lines.append(f"  Found: {c['found']}")
        lines.append(f"  Missing: {c['missing'] if c['missing'] is not None else 'unknown'}")
        lines.append(f"  Duplicate: {c['duplicate']}")
        lines.append(f"  Unresolved (validation issues): {c['unresolved']}")

    lines.append("")
    lines.append(
        "IMPORTANT: this report reflects what was actually retrieved and extracted in this "
        "run. It is not a claim of a complete or fully cross-verified dataset — see the "
        "verification/completeness figures above for exactly how much of this has been "
        "independently confirmed."
    )
    return "\n".join(lines)
