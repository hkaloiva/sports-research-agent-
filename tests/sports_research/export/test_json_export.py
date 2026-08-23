import json
import tempfile
import unittest
from pathlib import Path

from sports_research.export.json_export import export_json
from sports_research.models.event_result import make_event_result
from sports_research.research.engine import ResearchOutcome


class TestExportJSON(unittest.TestCase):
    def test_round_trips_records_and_metadata(self):
        event = make_event_result(
            sport="football", competition="PL", season="2020-2021", date="2020-08-15",
            participants=[{"name": "A", "role": "home", "score": 1}, {"name": "B", "role": "away", "score": 0}],
            status="completed", result="home_win",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        outcome = ResearchOutcome(
            request={"raw_query": "q", "status": "ready"}, plan={"search_queries": []},
            records=[event], sources=[], completeness={"expected": None, "found": 1, "duplicate": 0, "unresolved": 0, "missing": None},
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            export_json(outcome, path)
            payload = json.loads(path.read_text())

        self.assertEqual(payload["records"][0]["event_id"], event["event_id"])
        self.assertEqual(payload["request"]["raw_query"], "q")
        self.assertEqual(payload["completeness"]["found"], 1)


if __name__ == "__main__":
    unittest.main()
