import unittest

from sports_research.extraction.normalize import normalize_date, normalize_name, normalize_score


class TestNormalizeDate(unittest.TestCase):
    def test_iso_date_passes_through(self):
        self.assertEqual(normalize_date("2003-08-16"), "2003-08-16")

    def test_ddmmyyyy_slash_form(self):
        self.assertEqual(normalize_date("16/08/2003"), "2003-08-16")

    def test_day_month_name_year(self):
        self.assertEqual(normalize_date("16 August 2003"), "2003-08-16")

    def test_month_name_day_year(self):
        self.assertEqual(normalize_date("August 16, 2003"), "2003-08-16")

    def test_unparseable_text_returns_none(self):
        self.assertIsNone(normalize_date("sometime last year"))

    def test_invalid_calendar_date_returns_none(self):
        self.assertIsNone(normalize_date("2003-13-99"))


class TestNormalizeName(unittest.TestCase):
    def test_strips_footnote_markers(self):
        self.assertEqual(normalize_name("Arsenal[1]"), "Arsenal")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_name("  Manchester   United  "), "Manchester United")


class TestNormalizeScore(unittest.TestCase):
    def test_parses_integer(self):
        self.assertEqual(normalize_score("2"), 2)

    def test_non_numeric_returns_none(self):
        self.assertIsNone(normalize_score("two"))

    def test_never_rounds_a_decimal(self):
        self.assertIsNone(normalize_score("2.5"))


if __name__ == "__main__":
    unittest.main()
