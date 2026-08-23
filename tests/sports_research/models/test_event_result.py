import unittest

from sports_research.models.event_result import (
    build_named_event_id,
    build_two_participant_event_id,
    derive_two_participant_result,
    make_event_result,
    slugify,
)


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify("Manchester United"), "manchester-united")

    def test_strips_punctuation(self):
        self.assertEqual(slugify("St. James' Park!"), "st-james-park")


class TestDeriveTwoParticipantResult(unittest.TestCase):
    def test_home_win(self):
        participants = [{"role": "home", "score": 2}, {"role": "away", "score": 1}]
        self.assertEqual(derive_two_participant_result(participants), "home_win")

    def test_away_win(self):
        participants = [{"role": "home", "score": 0}, {"role": "away", "score": 3}]
        self.assertEqual(derive_two_participant_result(participants), "away_win")

    def test_draw(self):
        participants = [{"role": "home", "score": 1}, {"role": "away", "score": 1}]
        self.assertEqual(derive_two_participant_result(participants), "draw")

    def test_raises_without_both_roles(self):
        with self.assertRaises(ValueError):
            derive_two_participant_result([{"role": "competitor", "score": 1}])

    def test_raises_without_numeric_scores(self):
        with self.assertRaises(ValueError):
            derive_two_participant_result([{"role": "home", "score": None}, {"role": "away", "score": 1}])


class TestEventIdBuilders(unittest.TestCase):
    def test_two_participant_event_id(self):
        event_id = build_two_participant_event_id("football", "Premier League", "2003-2004", "2003-08-16", "Arsenal", "Everton")
        self.assertEqual(event_id, "football:premier-league:2003-2004:2003-08-16:arsenal-vs-everton")

    def test_named_event_id(self):
        event_id = build_named_event_id("tennis", "Wimbledon", "2021", "2021-07-11", "Men's Singles Final")
        self.assertEqual(event_id, "tennis:wimbledon:2021:2021-07-11:men-s-singles-final")


class TestMakeEventResult(unittest.TestCase):
    def test_two_participant_shape(self):
        participants = [{"name": "Arsenal", "role": "home", "score": 2}, {"name": "Everton", "role": "away", "score": 1}]
        event = make_event_result(
            sport="football", competition="Premier League", season="2003-2004", date="2003-08-16",
            participants=participants, status="completed", result="home_win",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        self.assertEqual(event["event_id"], "football:premier-league:2003-2004:2003-08-16:arsenal-vs-everton")
        self.assertEqual(event["verification_status"], "unverified")
        self.assertNotIn("round", event)
        self.assertNotIn("location", event)

    def test_placement_shape_uses_event_name(self):
        participants = [{"name": "Nyjah Huston", "role": "competitor", "placement": 1}]
        event = make_event_result(
            sport="skateboarding", competition="SLS", season="2015", date="2015-09-20",
            participants=participants, status="completed", result="win", event_name="World Championship",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        self.assertEqual(event["event_id"], "skateboarding:sls:2015:2015-09-20:world-championship")
        self.assertEqual(event["event_name"], "World Championship")

    def test_optional_fields_included_only_when_provided(self):
        participants = [{"name": "A", "role": "home", "score": 1}, {"name": "B", "role": "away", "score": 0}]
        event = make_event_result(
            sport="football", competition="X", season="2020", date="2020-01-01", participants=participants,
            status="completed", result="home_win", round="Final", location={"city": "London"}, notes="note",
            source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
        )
        self.assertEqual(event["round"], "Final")
        self.assertEqual(event["location"], {"city": "London"})
        self.assertEqual(event["notes"], "note")


if __name__ == "__main__":
    unittest.main()
