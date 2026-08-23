import unittest

from sports_research.validation.conflicts import classify_group


def _event(score1, score2, result="home_win"):
    return {
        "result": result,
        "participants": [{"name": "A", "score": score1}, {"name": "B", "score": score2}],
    }


class TestClassifyGroup(unittest.TestCase):
    def test_single_source_is_unverified(self):
        outcome = classify_group([_event(2, 1)], ["a.com"])
        self.assertEqual(outcome["verification_status"], "unverified")

    def test_two_agreeing_independent_domains_are_verified(self):
        outcome = classify_group([_event(2, 1), _event(2, 1)], ["a.com", "b.com"])
        self.assertEqual(outcome["verification_status"], "verified")
        self.assertEqual(outcome["disagreeing_indices"], [])

    def test_two_agreeing_same_domain_are_not_verified(self):
        outcome = classify_group([_event(2, 1), _event(2, 1)], ["a.com", "a.com"])
        self.assertEqual(outcome["verification_status"], "unverified")

    def test_disagreement_is_preserved_not_overwritten(self):
        outcome = classify_group([_event(2, 1), _event(1, 1, result="draw")], ["a.com", "b.com"])
        self.assertEqual(outcome["verification_status"], "conflicting")
        self.assertEqual(outcome["agreeing_indices"], [0])
        self.assertEqual(outcome["disagreeing_indices"], [1])

    def test_never_verified_from_a_single_source_even_with_many_records(self):
        # three records, but all from the same domain — not independent corroboration
        outcome = classify_group([_event(2, 1)] * 3, ["a.com", "a.com", "a.com"])
        self.assertNotEqual(outcome["verification_status"], "verified")


if __name__ == "__main__":
    unittest.main()
