import unittest

from sports_research.models.event_result import make_event_result
from sports_research.validation.schema_validation import event_result_matches_scores, validate_event_result

BASE = dict(
    sport="football", competition="Premier League", season="2020-2021", date="2020-08-15",
    source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z",
)


def _two_participant(score1, score2, result, status="completed"):
    participants = [{"name": "A", "role": "home", "score": score1}, {"name": "B", "role": "away", "score": score2}]
    return make_event_result(participants=participants, status=status, result=result, **BASE)


class TestValidEventResults(unittest.TestCase):
    def test_correctly_derived_home_win_is_valid(self):
        self.assertEqual(validate_event_result(_two_participant(2, 1, "home_win")), [])

    def test_correctly_derived_draw_is_valid(self):
        self.assertEqual(validate_event_result(_two_participant(1, 1, "draw")), [])

    def test_placement_event_has_no_two_participant_rule_applied(self):
        participants = [{"name": "X", "role": "competitor", "placement": 1}, {"name": "Y", "role": "competitor", "placement": 2}]
        event = make_event_result(participants=participants, status="completed", result="win", event_name="Final", **BASE)
        self.assertEqual(validate_event_result(event), [])


class TestInvalidEventResults(unittest.TestCase):
    def test_wrong_result_for_scores_is_rejected(self):
        problems = validate_event_result(_two_participant(5, 0, "draw"))
        self.assertTrue(problems)

    def test_missing_required_field_is_rejected(self):
        event = _two_participant(2, 1, "home_win")
        del event["source_url"]
        self.assertTrue(validate_event_result(event))

    def test_result_on_a_postponed_event_is_rejected(self):
        event = _two_participant(None, None, "home_win", status="postponed")
        self.assertTrue(validate_event_result(event))


class TestEventResultMatchesScores(unittest.TestCase):
    def test_true_for_correct_away_win(self):
        self.assertTrue(event_result_matches_scores(_two_participant(0, 2, "away_win")))

    def test_false_for_incorrect_result(self):
        self.assertFalse(event_result_matches_scores(_two_participant(0, 2, "home_win")))


if __name__ == "__main__":
    unittest.main()
