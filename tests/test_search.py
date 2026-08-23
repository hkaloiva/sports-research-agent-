"""Tests for search.py — all use mocked backends, no live internet."""

import json
import unittest

from config import BASE_DIR
from planner import build_search_plan
from search import MalformedSearchHitError, build_search_execution, mock_backend
from validation import build_search_result_validator, validate_search_result

REQUESTS_DIR = BASE_DIR / "schema" / "examples" / "research_requests"
RETRIEVED_AT = "2026-08-23T12:00:00Z"


def _plan_for(name: str) -> dict:
    request = json.loads((REQUESTS_DIR / name).read_text())
    return build_search_plan(request)


class TestDeduplication(unittest.TestCase):
    def setUp(self):
        self.plan = _plan_for("01_team_season.json")
        self.query1, self.query2 = (q["query"] for q in self.plan["search_queries"][:2])

    def test_identical_urls_are_deduplicated_into_one_result(self):
        fixture = {
            self.query1: [{"title": "A", "url": "https://en.wikipedia.org/wiki/X"}],
            self.query2: [{"title": "A", "url": "https://en.wikipedia.org/wiki/X"}],
        }
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertEqual(len(execution["results"]), 1)

    def test_deduplication_is_exact_url_match_only_no_normalization(self):
        # trailing slash difference: NOT the same URL, must not be merged
        fixture = {
            self.query1: [{"title": "A", "url": "https://example.com/page"}],
            self.query2: [{"title": "A", "url": "https://example.com/page/"}],
        }
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertEqual(len(execution["results"]), 2)

    def test_duplicate_url_merges_query_used_and_keeps_first_seen_title(self):
        fixture = {
            self.query1: [{"title": "First Title", "url": "https://example.com/x"}],
            self.query2: [{"title": "Second Title", "url": "https://example.com/x"}],
        }
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        result = execution["results"][0]
        self.assertEqual(result["title"], "First Title")
        self.assertEqual(set(result["query_used"]), {self.query1, self.query2})

    def test_same_domain_different_urls_are_kept_as_separate_results(self):
        fixture = {
            self.query1: [
                {"title": "Page A", "url": "https://en.wikipedia.org/wiki/A"},
                {"title": "Page B", "url": "https://en.wikipedia.org/wiki/B"},
            ],
        }
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        urls = {r["url"] for r in execution["results"]}
        self.assertEqual(urls, {"https://en.wikipedia.org/wiki/A", "https://en.wikipedia.org/wiki/B"})
        self.assertEqual(len(execution["results"]), 2)


class TestProvenanceIsPreserved(unittest.TestCase):
    def setUp(self):
        self.plan = _plan_for("01_team_season.json")
        self.query = self.plan["search_queries"][0]["query"]

    def test_url_is_preserved_exactly(self):
        weird_url = "https://example.com/path?q=Arsenal%202003%2F04&x=1#frag"
        fixture = {self.query: [{"title": "T", "url": weird_url}]}
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertEqual(execution["results"][0]["url"], weird_url)

    def test_query_used_records_which_query_produced_the_result(self):
        fixture = {self.query: [{"title": "T", "url": "https://example.com/a"}]}
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertEqual(execution["results"][0]["query_used"], [self.query])

    def test_domain_is_derived_from_the_url(self):
        fixture = {self.query: [{"title": "T", "url": "https://Sub.Example.COM/a"}]}
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertEqual(execution["results"][0]["domain"], "sub.example.com")

    def test_missing_snippet_is_null_not_fabricated(self):
        fixture = {self.query: [{"title": "T", "url": "https://example.com/a"}]}
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertIsNone(execution["results"][0]["snippet"])

    def test_provider_and_timestamp_are_recorded(self):
        fixture = {self.query: [{"title": "T", "url": "https://example.com/a"}]}
        execution = build_search_execution(self.plan, mock_backend(fixture), "my_provider", RETRIEVED_AT)
        self.assertEqual(execution["provider"], "my_provider")
        self.assertEqual(execution["executed_at"], RETRIEVED_AT)
        self.assertEqual(execution["results"][0]["provider"], "my_provider")
        self.assertEqual(execution["results"][0]["retrieved_at"], RETRIEVED_AT)

    def test_research_request_id_matches_the_plan(self):
        fixture = {self.query: [{"title": "T", "url": "https://example.com/a"}]}
        execution = build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        self.assertEqual(execution["research_request_id"], self.plan["research_request_id"])


class TestNeverFabricates(unittest.TestCase):
    def setUp(self):
        self.plan = _plan_for("01_team_season.json")
        self.query = self.plan["search_queries"][0]["query"]

    def test_hit_missing_url_raises_instead_of_inventing_one(self):
        fixture = {self.query: [{"title": "T"}]}
        with self.assertRaises(MalformedSearchHitError):
            build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)

    def test_hit_missing_title_raises_instead_of_inventing_one(self):
        fixture = {self.query: [{"url": "https://example.com/a"}]}
        with self.assertRaises(MalformedSearchHitError):
            build_search_execution(self.plan, mock_backend(fixture), "mock", RETRIEVED_AT)

    def test_query_with_no_hits_yields_no_results_not_an_error(self):
        execution = build_search_execution(self.plan, mock_backend({}), "mock", RETRIEVED_AT)
        self.assertEqual(execution["results"], [])
        self.assertEqual(execution["queries_executed"], [q["query"] for q in self.plan["search_queries"]])


class TestResultsValidateAgainstSchema(unittest.TestCase):
    def test_generated_results_validate(self):
        plan = _plan_for("02_head_to_head.json")
        query = plan["search_queries"][0]["query"]
        fixture = {
            query: [
                {"title": "Head to head", "url": "https://en.wikipedia.org/wiki/Merseyside_derby", "snippet": "History of the fixture."},
            ]
        }
        execution = build_search_execution(plan, mock_backend(fixture), "mock", RETRIEVED_AT)
        validator = build_search_result_validator()
        for result in execution["results"]:
            self.assertEqual(validate_search_result(result, validator), [])


if __name__ == "__main__":
    unittest.main()
