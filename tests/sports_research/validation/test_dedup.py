import unittest

from sports_research.validation.dedup import group_duplicate_events


def _event(sport="football", competition="PL", date="2020-01-01", names=("A", "B")):
    return {"sport": sport, "competition": competition, "date": date,
            "participants": [{"name": n} for n in names]}


class TestGroupDuplicateEvents(unittest.TestCase):
    def test_identical_signature_events_are_grouped(self):
        events = [_event(), _event(), _event(competition="Other")]
        groups = group_duplicate_events(events)
        self.assertEqual(groups, [[0, 1]])

    def test_no_duplicates_returns_empty(self):
        events = [_event(date="2020-01-01"), _event(date="2020-01-02")]
        self.assertEqual(group_duplicate_events(events), [])

    def test_participant_name_case_and_order_are_normalized(self):
        events = [_event(names=("Arsenal", "Everton")), _event(names=("everton", "ARSENAL"))]
        self.assertEqual(group_duplicate_events(events), [[0, 1]])

    def test_different_participants_same_date_are_not_grouped(self):
        events = [_event(names=("A", "B")), _event(names=("C", "D"))]
        self.assertEqual(group_duplicate_events(events), [])


if __name__ == "__main__":
    unittest.main()
