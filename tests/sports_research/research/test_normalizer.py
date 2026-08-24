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

    def test_sport_defaults_to_football_when_no_competition_named(self):
        # docs/research-request.md § Defaults, rule 2 — a real bug found by
        # actually running the packaged Windows exe: this default was
        # documented but never implemented, so every query without one of
        # the exact known competition phrases got stuck asking for a sport
        # that was already obvious from context (or, for the literal word
        # "football", stated outright).
        request = normalize_request("Search all Man Utd football club game results for season 2002/2003")
        self.assertEqual(request["constraints"]["sport"]["value"], "football")
        self.assertEqual(request["constraints"]["sport"]["source"], "inferred")
        fields = {c["field"] for c in request["clarifications_needed"]}
        self.assertNotIn("sport", fields)

    def test_ambiguous_team_alias_still_gets_a_defaulted_sport(self):
        # 'United' remains ambiguous (needs clarification), but the sport
        # is unambiguous from context — the two are independent.
        request = normalize_request("Show me United's matches from last season.")
        self.assertEqual(request["constraints"]["sport"]["value"], "football")
        fields = {c["field"] for c in request["clarifications_needed"]}
        self.assertNotIn("sport", fields)

    def test_sport_is_not_defaulted_when_a_different_unsupported_sport_is_named(self):
        request = normalize_request("Find every basketball result from the 2003 season.")
        self.assertNotIn("sport", request["constraints"])
        fields = {c["field"] for c in request["clarifications_needed"]}
        self.assertIn("sport", fields)

    def test_four_digit_slash_four_digit_season_form(self):
        # '2002/2003' (both halves 4 digits) wasn't matched by either the
        # '2003/04' or '2003-2004' season patterns and silently fell back
        # to just the bare year '2002' — found via the exact query above.
        request = normalize_request("Man Utd results for season 2002/2003")
        season = request["constraints"]["season"]
        self.assertEqual(season["value"], "2002-2003")
        self.assertEqual(season["raw_value"], "2002/2003")

    def test_leading_search_verb_is_not_swept_into_the_team_name(self):
        # 'Search' (capitalized as the sentence's first word) wasn't in
        # the stopword list, so it leaked into the extracted team name
        # as 'Search Man Utd' instead of 'Man Utd'.
        request = normalize_request("Search all Man Utd football club game results for season 2002/2003")
        self.assertEqual(request["constraints"]["teams"]["value"], ["Man Utd"])


if __name__ == "__main__":
    unittest.main()
