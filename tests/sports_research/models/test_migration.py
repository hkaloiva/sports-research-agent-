import json
import unittest

from config import BASE_DIR
from sports_research.models.migration import migrate_result_record_to_event_result
from sports_research.validation.schema_validation import validate_event_result

DATASET_PATH = BASE_DIR / "data" / "raw" / "test_results.json"


class TestMigration(unittest.TestCase):
    def test_migrates_every_record_in_the_step3_dataset_validly(self):
        records = json.loads(DATASET_PATH.read_text())
        for record in records:
            with self.subTest(event_id=record["event_id"]):
                event = migrate_result_record_to_event_result(record)
                self.assertEqual(validate_event_result(event), [])

    def test_preserves_event_id_sport_competition_season_date(self):
        record = json.loads(DATASET_PATH.read_text())[0]
        event = migrate_result_record_to_event_result(record)
        for field in ("event_id", "sport", "competition", "season", "date"):
            self.assertEqual(event[field], record[field])

    def test_home_away_become_two_participants(self):
        record = json.loads(DATASET_PATH.read_text())[0]
        event = migrate_result_record_to_event_result(record)
        self.assertEqual(len(event["participants"]), 2)
        home = next(p for p in event["participants"] if p["role"] == "home")
        away = next(p for p in event["participants"] if p["role"] == "away")
        self.assertEqual(home["name"], record["home_team"])
        self.assertEqual(home["score"], record["home_score"])
        self.assertEqual(away["name"], record["away_team"])
        self.assertEqual(away["score"], record["away_score"])

    def test_venue_becomes_location(self):
        records = json.loads(DATASET_PATH.read_text())
        record_with_venue = next(r for r in records if "venue" in r)
        event = migrate_result_record_to_event_result(record_with_venue)
        self.assertEqual(event["location"], record_with_venue["venue"])

    def test_absent_optional_fields_stay_absent(self):
        records = json.loads(DATASET_PATH.read_text())
        record_without_round = next(r for r in records if "round" not in r)
        event = migrate_result_record_to_event_result(record_without_round)
        self.assertNotIn("round", event)


if __name__ == "__main__":
    unittest.main()
