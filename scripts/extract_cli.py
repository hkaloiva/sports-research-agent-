#!/usr/bin/env python3
"""Extract canonical result records from a raw source-content text file,
then validate them (a separate step — see extractor.py's docstring).

    python3 scripts/extract_cli.py <raw_content.txt> \\
        --sport football --competition "Premier League" --season 2003-2004 \\
        --team Arsenal --source "..." --source-url "..." --source-accessed-at "..."

<raw_content.txt> uses the pipe-delimited line format documented in
extractor.py — real source content in a live run (see docs/extraction.md
for why no live run has been performed yet), a saved/mock fixture in
tests.

Performs no cross-source verification and no CSV/Excel export.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor import extract_records  # noqa: E402
from validation import build_validator, validate_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("content_file", type=Path, help="Path to raw source-content text (pipe-delimited match log lines).")
    parser.add_argument("--sport", default="football")
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--source", required=True, help="Name/identifier of the source, e.g. 'FBref.com'.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-accessed-at", help="ISO 8601 timestamp; defaults to now (UTC) if omitted.")
    parser.add_argument("--out", type=Path, help="Write the extracted (and validated) records here as a JSON array.")
    args = parser.parse_args()

    source_accessed_at = args.source_accessed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_text = args.content_file.read_text()

    extraction = extract_records(
        raw_text,
        sport=args.sport,
        competition=args.competition,
        season=args.season,
        team=args.team,
        source=args.source,
        source_url=args.source_url,
        source_accessed_at=source_accessed_at,
    )

    validator = build_validator()
    validation_problems = {}
    for record in extraction.records:
        problems = validate_record(record, validator)
        if problems:
            validation_problems[record["event_id"]] = problems

    print(f"Extracted {len(extraction.records)} record(s) from {args.content_file}")
    print(f"Ambiguous/unparseable line(s): {len(extraction.ambiguous)}")
    for issue in extraction.ambiguous:
        print(f"  line {issue['line_number']}: {issue['reason']} -> {issue['raw_line']!r}")

    if validation_problems:
        print(f"\n{len(validation_problems)} record(s) FAILED validation:")
        for event_id, problems in validation_problems.items():
            print(f"  {event_id}:")
            for problem in problems:
                print(f"    {problem}")
    else:
        print("\nAll extracted records passed validation against result_record.schema.json.")

    if args.out:
        args.out.write_text(json.dumps(extraction.records, indent=2) + "\n")
        print(f"\nWrote {len(extraction.records)} record(s) to {args.out}")

    return 1 if validation_problems else 0


if __name__ == "__main__":
    sys.exit(main())
