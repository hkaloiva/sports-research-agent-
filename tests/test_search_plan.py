"""Tests for the deterministic SearchPlan generator (planner.py)."""

import json
import unittest

from config import BASE_DIR
from planner import AmbiguousRequestError, build_search_plan
from validation import build_plan_validator, validate_plan

REQUESTS_DIR = BASE_DIR / "schema" / "examples" / "research_requests"


def _load_request(name: str) -> dict:
    return json.loads((REQUESTS_DIR / name).read_text())


class TestTeamCompetitionSeason(unittest.TestCase):
    """Category 1: team + competition + season."""

    @classmethod
    def setUpClass(cls):
        cls.request = _load_request("01_team_season.json")
        cls.plan = build_search_plan(cls.request)
        cls.validator = build_plan_validator()

    def test_plan_validates_against_schema(self):
        self.assertEqual(validate_plan(self.plan, self.validator), [])

    def test_generates_multiple_queries(self):
        self.assertGreaterEqual(len(self.plan["search_queries"]), 3)

    def test_queries_mention_team_and_season_in_more_than_one_form(self):
        queries = " | ".join(q["query"] for q in self.plan["search_queries"])
        self.assertIn("Arsenal", queries)
        # Season appears in at least two different textual forms across queries.
        self.assertIn("2003/04", queries)
        self.assertIn("2003", queries)
        self.assertIn("2004", queries)

    def test_search_scope_preserves_request_provenance(self):
        scope = self.plan["search_scope"]
        self.assertEqual(scope["sport"], self.request["constraints"]["sport"])
        self.assertEqual(scope["season"], self.request["constraints"]["season"])
        self.assertEqual(scope["teams"], self.request["constraints"]["teams"])

    def test_expected_result_count_uses_documented_premier_league_rule(self):
        self.assertIn("expected_result_count", self.plan)
        self.assertEqual(self.plan["expected_result_count"]["value"], 38)
        self.assertIn("basis", self.plan["expected_result_count"])

    def test_pagination_is_bounded_when_season_is_known(self):
        self.assertEqual(self.plan["pagination_strategy"]["approach"], "bounded_range_lookup")

    def test_verification_requires_second_source(self):
        self.assertTrue(self.plan["verification_strategy"]["requires_second_source"])


class TestHeadToHead(unittest.TestCase):
    """Category 2: head-to-head between two teams."""

    @classmethod
    def setUpClass(cls):
        cls.request = _load_request("02_head_to_head.json")
        cls.plan = build_search_plan(cls.request)
        cls.validator = build_plan_validator()

    def test_plan_validates_against_schema(self):
        self.assertEqual(validate_plan(self.plan, self.validator), [])

    def test_generates_multiple_queries_mentioning_both_teams(self):
        self.assertGreaterEqual(len(self.plan["search_queries"]), 2)
        for q in self.plan["search_queries"]:
            self.assertIn("Liverpool", q["query"])
            self.assertIn("Everton", q["query"])

    def test_no_season_in_scope_since_none_was_requested(self):
        self.assertNotIn("season", self.plan["search_scope"])
        self.assertIn("teams", self.plan["search_scope"])
        self.assertEqual(self.plan["search_scope"]["teams"]["value"], ["Liverpool", "Everton"])

    def test_no_expected_result_count_without_a_season(self):
        self.assertNotIn("expected_result_count", self.plan)

    def test_pagination_is_unbounded_without_season_or_date_range(self):
        self.assertEqual(self.plan["pagination_strategy"]["approach"], "iterative_unbounded_lookup")


class TestCompetitionDateRange(unittest.TestCase):
    """Category 3: competition over a date range."""

    @classmethod
    def setUpClass(cls):
        cls.request = _load_request("03_competition_date_range.json")
        cls.plan = build_search_plan(cls.request)
        cls.validator = build_plan_validator()

    def test_plan_validates_against_schema(self):
        self.assertEqual(validate_plan(self.plan, self.validator), [])

    def test_generates_multiple_queries_mentioning_the_competition(self):
        self.assertGreaterEqual(len(self.plan["search_queries"]), 2)
        for q in self.plan["search_queries"]:
            self.assertIn("UEFA Champions League", q["query"])

    def test_scope_carries_the_date_range_not_a_season(self):
        scope = self.plan["search_scope"]
        self.assertNotIn("season", scope)
        self.assertEqual(scope["date_from"]["value"], "2018-01-01")
        self.assertEqual(scope["date_to"]["value"], "2018-12-31")

    def test_pagination_is_bounded_by_the_explicit_date_range(self):
        self.assertEqual(self.plan["pagination_strategy"]["approach"], "bounded_range_lookup")


class TestResultTypeFiltering(unittest.TestCase):
    """Category 4: filtering by result type (+ home/away)."""

    @classmethod
    def setUpClass(cls):
        cls.request = _load_request("04_result_type_filter.json")
        cls.plan = build_search_plan(cls.request)
        cls.validator = build_plan_validator()

    def test_plan_validates_against_schema(self):
        self.assertEqual(validate_plan(self.plan, self.validator), [])

    def test_at_least_one_query_reflects_the_result_type(self):
        queries = " | ".join(q["query"] for q in self.plan["search_queries"])
        self.assertIn("draw", queries)

    def test_scope_carries_result_types_and_home_away(self):
        scope = self.plan["search_scope"]
        self.assertEqual(scope["result_types"]["value"], ["draw"])
        self.assertEqual(scope["home_away"]["value"], "away")


class TestAmbiguousRequestProducesNoPlan(unittest.TestCase):
    """Category 5: an ambiguous ResearchRequest must NOT produce a SearchPlan."""

    def test_needs_clarification_request_raises_instead_of_planning(self):
        request = _load_request("05_ambiguous_needs_clarification.json")
        self.assertEqual(request["status"], "needs_clarification")
        with self.assertRaises(AmbiguousRequestError):
            build_search_plan(request)


class TestPlannerDoesNotClaimResults(unittest.TestCase):
    """The planner must never assert that a source exists or a query ran."""

    def test_expected_result_count_is_framed_as_an_estimate(self):
        request = _load_request("01_team_season.json")
        plan = build_search_plan(request)
        basis = plan["expected_result_count"]["basis"].lower()
        self.assertIn("estimate", basis)
        self.assertNotIn("found", basis)

    def test_pagination_notes_are_framed_as_heuristic(self):
        request = _load_request("01_team_season.json")
        plan = build_search_plan(request)
        self.assertIn("heuristic", plan["pagination_strategy"]["notes"].lower())


class TestDifferentRequestsProduceDifferentQueries(unittest.TestCase):
    def test_team_season_and_head_to_head_queries_do_not_match(self):
        plan1 = build_search_plan(_load_request("01_team_season.json"))
        plan2 = build_search_plan(_load_request("02_head_to_head.json"))
        queries1 = {q["query"] for q in plan1["search_queries"]}
        queries2 = {q["query"] for q in plan2["search_queries"]}
        self.assertTrue(queries1.isdisjoint(queries2))

    def test_all_four_plannable_examples_have_distinct_query_sets(self):
        names = [
            "01_team_season.json",
            "02_head_to_head.json",
            "03_competition_date_range.json",
            "04_result_type_filter.json",
        ]
        query_sets = [
            frozenset(q["query"] for q in build_search_plan(_load_request(n))["search_queries"])
            for n in names
        ]
        for i in range(len(query_sets)):
            for j in range(i + 1, len(query_sets)):
                with self.subTest(a=names[i], b=names[j]):
                    self.assertNotEqual(query_sets[i], query_sets[j])

    def test_same_request_produces_the_same_plan_id_deterministically(self):
        request = _load_request("01_team_season.json")
        plan_a = build_search_plan(request)
        plan_b = build_search_plan(request)
        self.assertEqual(plan_a["research_request_id"], plan_b["research_request_id"])

    def test_requires_second_source_reflects_verification_setting(self):
        base = _load_request("02_head_to_head.json")
        required = json.loads(json.dumps(base))
        required["constraints"]["verification"] = {"value": "required", "source": "explicit"}
        not_required = json.loads(json.dumps(base))
        not_required["constraints"]["verification"] = {"value": "not_required", "source": "explicit"}

        plan_required = build_search_plan(required)
        plan_not_required = build_search_plan(not_required)

        self.assertTrue(plan_required["verification_strategy"]["requires_second_source"])
        self.assertFalse(plan_not_required["verification_strategy"]["requires_second_source"])


if __name__ == "__main__":
    unittest.main()
