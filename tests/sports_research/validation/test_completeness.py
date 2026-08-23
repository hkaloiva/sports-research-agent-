import unittest

from sports_research.validation.completeness import check_completeness


class TestCheckCompleteness(unittest.TestCase):
    def test_missing_is_computed_when_expected_known(self):
        result = check_completeness(found_count=36, duplicate_count=1, unresolved_count=0, expected_count=38)
        self.assertEqual(result["missing"], 2)

    def test_missing_is_none_without_a_documented_expected_count(self):
        result = check_completeness(found_count=10, duplicate_count=0, unresolved_count=0, expected_count=None)
        self.assertIsNone(result["missing"])
        self.assertIsNone(result["expected"])

    def test_missing_never_goes_negative(self):
        result = check_completeness(found_count=40, duplicate_count=0, unresolved_count=0, expected_count=38)
        self.assertEqual(result["missing"], 0)


if __name__ == "__main__":
    unittest.main()
