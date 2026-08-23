import csv
import tempfile
import unittest
from pathlib import Path

from sports_research.export.csv_export import export_csv
from sports_research.models.event_result import make_event_result

BASE = dict(sport="football", competition="Premier League", season="2020-2021", date="2020-08-15",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z")


class TestExportCSV(unittest.TestCase):
    def test_one_row_per_participant(self):
        participants = [{"name": "A", "role": "home", "score": 2}, {"name": "B", "role": "away", "score": 1}]
        event = make_event_result(participants=participants, status="completed", result="home_win", **BASE)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            export_csv([event], path)
            with open(path) as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["participant_name"], "A")
        self.assertEqual(rows[0]["event_id"], event["event_id"])
        self.assertEqual(rows[1]["participant_role"], "away")

    def test_handles_a_placement_event_with_more_than_two_participants(self):
        participants = [{"name": "A", "role": "competitor", "placement": 1},
                         {"name": "B", "role": "competitor", "placement": 2},
                         {"name": "C", "role": "competitor", "placement": 3}]
        event = make_event_result(participants=participants, status="completed", result="win",
                                   event_name="Final", **BASE)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            export_csv([event], path)
            with open(path) as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
