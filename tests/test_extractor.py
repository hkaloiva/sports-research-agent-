"""Tests for extractor.py — uses only the saved synthetic fixture, no
live retrieval (WebFetch was confirmed blocked in this environment; see
docs/extraction.md)."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

from config import BASE_DIR
from extractor import extract_records
from validation import build_validator, validate_record

FIXTURE_PATH = BASE_DIR / "tests" / "fixtures" / "synthetic_match_log.txt"
CONTEXT = dict(
    sport="football",
    competition="Premier League",
    season="2003-2004",
    team="Arsenal",
    source="synthetic test fixture",
    source_url="https://example.invalid/fixture",
    source_accessed_at="2026-08-23T12:00:00Z",
)


def _extract():
    return extract_records(FIXTURE_PATH.read_text(), **CONTEXT)


class TestExtraction(unittest.TestCase):
    def test_extracts_exactly_the_well_formed_rows(self):
        result = _extract()
        self.assertEqual(len(result.records), 5)

    def test_home_row_assigns_team_as_home(self):
        result = _extract()
        record = result.records[0]
        self.assertEqual(record["home_team"], "Arsenal")
        self.assertEqual(record["away_team"], "Test City")
        self.assertEqual(record["home_score"], 2)
        self.assertEqual(record["away_score"], 1)
        self.assertEqual(record["result"], "home_win")

    def test_away_row_swaps_scores_correctly(self):
        result = _extract()
        record = result.records[1]  # Away|Sample United|0|3 (Arsenal scored 0, conceded 3)
        self.assertEqual(record["home_team"], "Sample United")
        self.assertEqual(record["away_team"], "Arsenal")
        self.assertEqual(record["home_score"], 3)
        self.assertEqual(record["away_score"], 0)
        self.assertEqual(record["result"], "home_win")

    def test_draw_is_derived_correctly(self):
        result = _extract()
        record = result.records[2]
        self.assertEqual(record["result"], "draw")

    def test_missing_round_is_omitted_not_invented(self):
        result = _extract()
        record = result.records[3]  # the row with an empty round field
        self.assertNotIn("round", record)

    def test_status_is_always_completed(self):
        result = _extract()
        for record in result.records:
            self.assertEqual(record["status"], "completed")

    def test_verification_status_is_always_unverified(self):
        result = _extract()
        for record in result.records:
            self.assertEqual(record["verification_status"], "unverified")

    def test_venue_field_is_never_invented(self):
        result = _extract()
        for record in result.records:
            self.assertNotIn("venue", record)

    def test_provenance_fields_are_threaded_through_unchanged(self):
        result = _extract()
        for record in result.records:
            self.assertEqual(record["source"], CONTEXT["source"])
            self.assertEqual(record["source_url"], CONTEXT["source_url"])
            self.assertEqual(record["source_accessed_at"], CONTEXT["source_accessed_at"])

    def test_event_id_format(self):
        result = _extract()
        self.assertEqual(
            result.records[0]["event_id"],
            "football:premier-league:2003-2004:2003-08-16:arsenal-vs-test-city",
        )


class TestAmbiguousRowsAreReportedNotGuessed(unittest.TestCase):
    def test_four_malformed_rows_are_reported(self):
        result = _extract()
        self.assertEqual(len(result.ambiguous), 4)

    def test_wrong_field_count_is_reported(self):
        result = _extract()
        reasons = [a["reason"] for a in result.ambiguous]
        self.assertTrue(any("6 pipe-delimited fields" in r for r in reasons))

    def test_bad_venue_is_reported(self):
        result = _extract()
        reasons = [a["reason"] for a in result.ambiguous]
        self.assertTrue(any("not 'Home' or 'Away'" in r for r in reasons))

    def test_non_numeric_score_is_reported(self):
        result = _extract()
        reasons = [a["reason"] for a in result.ambiguous]
        self.assertTrue(any("non-negative integer" in r for r in reasons))

    def test_bad_date_format_is_reported(self):
        result = _extract()
        reasons = [a["reason"] for a in result.ambiguous]
        self.assertTrue(any("ISO 8601" in r for r in reasons))

    def test_ambiguous_rows_never_appear_as_records(self):
        result = _extract()
        opponents = {r["home_team"] for r in result.records} | {r["away_team"] for r in result.records}
        # None of the malformed rows' opponents should have produced a record.
        self.assertNotIn("Test City 2", opponents)


class TestExtractionIsSeparateFromValidation(unittest.TestCase):
    def test_extractor_module_does_not_import_validation(self):
        tree = ast.parse((BASE_DIR / "extractor.py").read_text())
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
        self.assertNotIn("validation", imported_names)

    def test_extracted_records_all_validate_against_the_canonical_schema(self):
        result = _extract()
        validator = build_validator()
        for record in result.records:
            with self.subTest(event_id=record["event_id"]):
                self.assertEqual(validate_record(record, validator), [])


class TestExtractCli(unittest.TestCase):
    def test_cli_runs_end_to_end_on_the_fixture(self):
        proc = subprocess.run(
            [
                sys.executable, str(BASE_DIR / "scripts" / "extract_cli.py"),
                str(FIXTURE_PATH),
                "--competition", "Premier League",
                "--season", "2003-2004",
                "--team", "Arsenal",
                "--source", "synthetic test fixture",
                "--source-url", "https://example.invalid/fixture",
                "--source-accessed-at", "2026-08-23T12:00:00Z",
            ],
            capture_output=True, text=True, cwd=BASE_DIR,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Extracted 5 record(s)", proc.stdout)
        self.assertIn("Ambiguous/unparseable line(s): 4", proc.stdout)
        self.assertIn("All extracted records passed validation", proc.stdout)


if __name__ == "__main__":
    unittest.main()
