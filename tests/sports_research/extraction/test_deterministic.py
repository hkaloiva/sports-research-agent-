import unittest

from sports_research.extraction.deterministic import extract_placement_event, extract_two_participant_events
from sports_research.validation.schema_validation import validate_event_result

CONTEXT = dict(sport="football", competition="Premier League", season="2003-2004",
               source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z")


class TestExtractTwoParticipantEvents(unittest.TestCase):
    def test_extracts_matches_under_a_date_heading(self):
        text = "2003-08-16:\nArsenal 2-1 Everton\nChelsea 1-1 Liverpool\n"
        result = extract_two_participant_events(text, **CONTEXT)
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.records[0]["date"], "2003-08-16")
        self.assertEqual(result.records[0]["result"], "home_win")
        self.assertEqual(result.records[1]["result"], "draw")

    def test_carries_the_date_forward_until_a_new_one_appears(self):
        text = "2003-08-16:\nArsenal 2-1 Everton\n2003-08-24:\nChelsea 3-0 Liverpool\n"
        result = extract_two_participant_events(text, **CONTEXT)
        self.assertEqual(result.records[0]["date"], "2003-08-16")
        self.assertEqual(result.records[1]["date"], "2003-08-24")

    def test_score_line_before_any_date_is_ambiguous_not_guessed(self):
        text = "Arsenal 2-1 Everton\n"
        result = extract_two_participant_events(text, **CONTEXT)
        self.assertEqual(result.records, [])
        self.assertEqual(len(result.ambiguous), 1)
        self.assertIn("no date established", result.ambiguous[0]["reason"])

    def test_all_records_validate_against_the_canonical_schema(self):
        text = "2003-08-16:\nArsenal 2-1 Everton\n"
        result = extract_two_participant_events(text, **CONTEXT)
        self.assertEqual(validate_event_result(result.records[0]), [])

    def test_away_win_correctly_assigns_scores(self):
        text = "2003-08-16:\nArsenal 0-3 Chelsea\n"
        result = extract_two_participant_events(text, **CONTEXT)
        record = result.records[0]
        self.assertEqual(record["result"], "away_win")
        home = next(p for p in record["participants"] if p["role"] == "home")
        away = next(p for p in record["participants"] if p["role"] == "away")
        self.assertEqual((home["name"], home["score"]), ("Arsenal", 0))
        self.assertEqual((away["name"], away["score"]), ("Chelsea", 3))


class TestExtractPlacementEvent(unittest.TestCase):
    def test_extracts_a_ranked_list_into_one_event(self):
        text = "1. Nyjah Huston - 93.5\n2. Shane O Neill - 88.2\n"
        result = extract_placement_event(
            text, sport="skateboarding", competition="SLS", season="2015",
            event_name="Final", date="2015-09-20",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        self.assertEqual(len(result.records), 1)
        participants = result.records[0]["participants"]
        self.assertEqual(participants[0]["placement"], 1)
        self.assertEqual(participants[0]["score"], 93.5)
        self.assertEqual(result.records[0]["result"], "win")

    def test_no_ranked_lines_produces_no_record(self):
        result = extract_placement_event(
            "nothing here", sport="s", competition="c", season="2020",
            event_name="e", date="2020-01-01",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        self.assertEqual(result.records, [])

    def test_record_validates_against_the_canonical_schema(self):
        text = "1. A\n2. B\n"
        result = extract_placement_event(
            text, sport="motorsport", competition="F1", season="1990",
            event_name="Brazilian Grand Prix", date="1990-03-25",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        self.assertEqual(validate_event_result(result.records[0]), [])


if __name__ == "__main__":
    unittest.main()
