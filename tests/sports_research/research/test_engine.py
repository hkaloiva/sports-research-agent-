"""Full-pipeline integration tests for ResearchEngine, entirely with
mocked SearchProvider/ContentProvider — no live internet."""

import unittest

from sports_research.extraction.engine import ExtractionEngine
from sports_research.research.engine import ResearchEngine
from sports_research.retrieval.base import ContentProvider, make_source_content
from sports_research.search.base import SearchProvider, SearchProviderError


class ArsenalMockSearch(SearchProvider):
    name = "mock_search"

    def search(self, query, max_results=10):
        return [
            {"title": "Arsenal 2003-04 season - Wikipedia", "url": "https://en.wikipedia.org/wiki/Arsenal_2003_04", "snippet": None},
            {"title": "Arsenal results 2003/04", "url": "https://example-stats.invalid/arsenal-2003-04", "snippet": None},
        ]


class ArsenalMockContent(ContentProvider):
    name = "mock_content"
    PAGES = {
        "https://en.wikipedia.org/wiki/Arsenal_2003_04": "2003-08-16:\nArsenal 2-1 Everton\nChelsea 1-1 Liverpool\n",
        "https://example-stats.invalid/arsenal-2003-04": "2003-08-16:\nArsenal 2-1 Everton\n2003-08-24:\nManchester United 4-0 Newcastle\n",
    }

    def fetch(self, url):
        text = self.PAGES.get(url)
        return make_source_content(
            url=url, final_url=url, http_status=200 if text else 404, title="t", text=text,
            retrieval_method=self.name, retrieved_at="2026-08-23T12:00:00Z",
            error=None if text else "not found",
        )


class SLSMockSearch(SearchProvider):
    name = "mock_search"

    def search(self, query, max_results=10):
        return [{"title": "2015 SLS results", "url": "https://example-sls.invalid/2015", "snippet": None}]


class SLSMockContent(ContentProvider):
    name = "mock_content"

    def fetch(self, url):
        text = "2015 SLS Nike World Championship Final Standings\n1. Nyjah Huston - 93.5\n2. Shane ONeill - 88.2\n"
        return make_source_content(
            url=url, final_url=url, http_status=200, title="t", text=text,
            retrieval_method=self.name, retrieved_at="2026-08-23T12:00:00Z", error=None,
        )


class FailingSearch(SearchProvider):
    name = "failing_search"

    def search(self, query, max_results=10):
        raise SearchProviderError("simulated outage")


class TestResearchEngineFootball(unittest.TestCase):
    def setUp(self):
        self.engine = ResearchEngine(ArsenalMockSearch(), ArsenalMockContent(), ExtractionEngine(use_local_llm=False))
        self.outcome = self.engine.run("Find every Arsenal Premier League result from the 2003/04 season.")

    def test_completes_all_eight_stages(self):
        self.assertEqual(len(self.outcome.stage_log), 8)

    def test_extracts_records_from_multiple_sources(self):
        self.assertEqual(len(self.outcome.records), 4)

    def test_duplicate_across_sources_is_detected_and_verified(self):
        self.assertEqual(len(self.outcome.duplicate_groups), 1)
        verified = [r for r in self.outcome.records if r["verification_status"] == "verified"]
        self.assertEqual(len(verified), 2)  # the two Arsenal-Everton copies

    def test_single_source_records_stay_unverified(self):
        unverified = [r for r in self.outcome.records if r["verification_status"] == "unverified"]
        self.assertGreaterEqual(len(unverified), 1)

    def test_no_validation_problems(self):
        self.assertEqual(self.outcome.validation_problems, {})

    def test_sources_are_recorded_with_type_classification(self):
        self.assertEqual(len(self.outcome.sources), 2)
        wiki_source = next(s for s in self.outcome.sources if "wikipedia" in s["domain"])
        self.assertEqual(wiki_source["source_type"], "sports_reference_site")


class TestResearchEngineNonFootballSport(unittest.TestCase):
    """The build spec explicitly calls this out as important: proving the
    system is not secretly football-specific."""

    def test_skateboarding_request_produces_a_placement_based_event(self):
        engine = ResearchEngine(SLSMockSearch(), SLSMockContent(), ExtractionEngine(use_local_llm=False))
        outcome = engine.run("Find the results of the 2015 Street League Skateboarding competitions.")

        self.assertEqual(len(outcome.records), 1)
        event = outcome.records[0]
        self.assertEqual(event["sport"], "skateboarding")
        self.assertEqual(len(event["participants"]), 2)
        self.assertEqual(event["participants"][0]["placement"], 1)
        self.assertEqual(outcome.validation_problems, {})


class TestResearchEngineHandlesFailureGracefully(unittest.TestCase):
    def test_search_provider_failure_does_not_crash_the_pipeline(self):
        engine = ResearchEngine(FailingSearch(), ArsenalMockContent(), ExtractionEngine(use_local_llm=False))
        outcome = engine.run("Find every Arsenal Premier League result from the 2003/04 season.")
        self.assertEqual(len(outcome.stage_log), 8)
        self.assertEqual(outcome.records, [])

    def test_content_retrieval_failure_is_recorded_and_pipeline_continues(self):
        class OnlyBrokenLinkSearch(SearchProvider):
            name = "mock_search"

            def search(self, query, max_results=10):
                return [{"title": "Dead link", "url": "https://example-stats.invalid/does-not-exist", "snippet": None}]

        engine = ResearchEngine(OnlyBrokenLinkSearch(), ArsenalMockContent(), ExtractionEngine(use_local_llm=False))
        outcome = engine.run("Find every Arsenal Premier League result from the 2003/04 season.")
        self.assertEqual(outcome.sources[0]["retrieval_status"], "http_error")
        self.assertEqual(outcome.records, [])

    def test_ambiguous_request_returns_before_searching(self):
        engine = ResearchEngine(FailingSearch(), ArsenalMockContent(), ExtractionEngine(use_local_llm=False))
        outcome = engine.run("Show me United's matches from last season.")
        self.assertTrue(outcome.clarification_needed)
        self.assertEqual(outcome.stage_log, ["[1/8] Understanding request"])


if __name__ == "__main__":
    unittest.main()
