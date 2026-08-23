"""Validates the full test dataset against the schema and business rules,
and confirms deliberately-broken records are rejected."""

import copy
import json
import unittest

from config import BASE_DIR
from validation import build_validator, validate_record

DATASET_PATH = BASE_DIR / "data" / "raw" / "test_results.json"


class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = build_validator()
        cls.records = json.loads(DATASET_PATH.read_text())

    def test_dataset_has_20_records(self):
        self.assertEqual(len(self.records), 20)

    def test_every_record_is_valid(self):
        for record in self.records:
            with self.subTest(event_id=record.get("event_id")):
                problems = validate_record(record, self.validator)
                self.assertEqual(problems, [])

    def test_every_record_is_completed_with_a_derived_result(self):
        for record in self.records:
            with self.subTest(event_id=record.get("event_id")):
                self.assertEqual(record["status"], "completed")
                self.assertIsInstance(record["home_score"], int)
                self.assertIsInstance(record["away_score"], int)
                self.assertIn(record["result"], ("home_win", "away_win", "draw"))

    def test_includes_at_least_two_world_cup_matches(self):
        count = sum(1 for r in self.records if r["competition"] == "FIFA World Cup")
        self.assertGreaterEqual(count, 2)

    def test_includes_at_least_two_champions_league_matches(self):
        count = sum(1 for r in self.records if r["competition"] == "UEFA Champions League")
        self.assertGreaterEqual(count, 2)

    def test_includes_at_least_two_premier_league_matches(self):
        count = sum(1 for r in self.records if r["competition"] == "Premier League")
        self.assertGreaterEqual(count, 2)

    def test_includes_a_match_before_2000(self):
        self.assertTrue(any(r["date"] < "2000-01-01" for r in self.records))

    def test_includes_a_match_after_2020(self):
        self.assertTrue(any(r["date"] > "2020-12-31" for r in self.records))

    def test_includes_all_three_outcome_types(self):
        results = {r["result"] for r in self.records}
        self.assertEqual(results, {"home_win", "away_win", "draw"})


class TestRejectsInvalidRecords(unittest.TestCase):
    """Deliberately break known-good records and confirm each is rejected."""

    @classmethod
    def setUpClass(cls):
        cls.validator = build_validator()
        cls.records = json.loads(DATASET_PATH.read_text())

    def _good_completed_record(self) -> dict:
        # The 1998 World Cup final record: France 3-0 Brazil, home_win.
        return copy.deepcopy(self.records[1])

    def test_rejects_invalid_score_result_combination(self):
        record = self._good_completed_record()
        record["home_score"] = 5
        record["away_score"] = 0
        record["result"] = "draw"  # wrong: 5-0 is not a draw
        problems = validate_record(record, self.validator)
        self.assertTrue(problems, "an invalid score/result combination should be rejected")

    def test_rejects_missing_required_field(self):
        record = self._good_completed_record()
        del record["source_url"]
        problems = validate_record(record, self.validator)
        self.assertTrue(problems, "a record missing a required field should be rejected")

    def test_rejects_postponed_match_with_a_score(self):
        record = self._good_completed_record()
        record["status"] = "postponed"
        record["home_score"] = 2
        record["away_score"] = 1
        record["result"] = "home_win"
        problems = validate_record(record, self.validator)
        self.assertTrue(problems, "a postponed match carrying a score should be rejected")


if __name__ == "__main__":
    unittest.main()
