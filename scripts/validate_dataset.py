#!/usr/bin/env python3
"""Validate data/raw/test_results.json against the schema and print a summary.

Run: python3 scripts/validate_dataset.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import BASE_DIR  # noqa: E402
from validation import build_validator, validate_record  # noqa: E402

DATASET_PATH = BASE_DIR / "data" / "raw" / "test_results.json"


def main() -> int:
    validator = build_validator()
    records = json.loads(DATASET_PATH.read_text())

    all_ok = True
    for record in records:
        problems = validate_record(record, validator)
        ok = not problems
        all_ok = all_ok and ok
        print(f"{record.get('event_id', '?')}: {'PASS' if ok else 'FAIL'}")
        for problem in problems:
            print(f"  {problem}")

    competitions = sorted({r["competition"] for r in records})
    dates = sorted(r["date"] for r in records)

    print()
    print(f"Records: {len(records)}")
    print(f"Competitions ({len(competitions)}): {', '.join(competitions)}")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
