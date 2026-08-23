import unittest

from sports_research.research.normalizer import normalize_request
from validation import build_request_validator, validate_request


class TestNormalizeRequest(unittest.TestCase):
    def setUp(self):
        self.validator = build_request_validator()

    def _assert_schema_valid(self, request):
        self.assertEqual(validate_request(request, self.validator), [])

    def test_football_team_season_request(self):
        request = normalize_request("Find every Arsenal Premier League result from the 2003/04 season.")
        self._assert_schema_valid(request)
        self.assertEqual(request["status"], "ready")
        self.assertEqual(request["constraints"]["competition"]["value"], "Premier League")
        self.assertEqual(request["constraints"]["sport"]["value"], "football")
        self.assertEqual(request["constraints"]["season"]["value"], "2003-2004")
        self.assertEqual(request["constraints"]["teams"]["value"], ["Arsenal"])

    def test_skateboarding_season_request_proves_not_football_specific(self):
        request = normalize_request("Find the results of the 2015 Street League Skateboarding competitions.")
        self._assert_schema_valid(request)
        self.assertEqual(request["status"], "ready")
        self.assertEqual(request["constraints"]["sport"]["value"], "skateboarding")
        self.assertEqual(request["constraints"]["competition"]["value"], "Street League Skateboarding")
        self.assertEqual(request["constraints"]["season"]["value"], "2015")

    def test_tennis_event_name_and_date_range_request(self):
        request = normalize_request("Find all Wimbledon men's singles finals from 2000 to 2025.")
        self._assert_schema_valid(request)
        self.assertEqual(request["constraints"]["sport"]["value"], "tennis")
        self.assertEqual(request["constraints"]["event_name"]["value"], "Men's Singles")
        self.assertEqual(request["constraints"]["date_from"]["value"], "2000-01-01")
        self.assertEqual(request["constraints"]["date_to"]["value"], "2025-12-31")

    def test_motorsport_season_request(self):
        request = normalize_request("Find every Formula 1 race result from the 1990 season.")
        self._assert_schema_valid(request)
        self.assertEqual(request["constraints"]["sport"]["value"], "motorsport")
        self.assertEqual(request["constraints"]["season"]["value"], "1990")

    def test_head_to_head_splits_two_participants(self):
        request = normalize_request("How have Liverpool and Everton done against each other in the Premier League?")
        self._assert_schema_valid(request)
        self.assertEqual(request["constraints"]["teams"]["value"], ["Liverpool", "Everton"])

    def test_ambiguous_team_alias_requires_clarification(self):
        request = normalize_request("Show me United's matches from last season.")
        self._assert_schema_valid(request)
        self.assertEqual(request["status"], "needs_clarification")
        fields = {c["field"] for c in request["clarifications_needed"]}
        self.assertIn("teams", fields)
        self.assertIn("season", fields)
        self.assertNotIn("teams", request["constraints"])

    def test_season_slash_form_is_explicit_with_raw_value_preserved(self):
        request = normalize_request("Arsenal Premier League 2003/04 results")
        season = request["constraints"]["season"]
        self.assertEqual(season["source"], "explicit")
        self.assertEqual(season["value"], "2003-2004")
        self.assertEqual(season["raw_value"], "2003/04")

    def test_sport_is_inferred_with_a_basis_not_explicit(self):
        request = normalize_request("Find every Arsenal Premier League result from the 2003/04 season.")
        sport = request["constraints"]["sport"]
        self.assertEqual(sport["source"], "inferred")
        self.assertIn("basis", sport)


if __name__ == "__main__":
    unittest.main()
