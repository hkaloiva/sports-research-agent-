import unittest

from sports_research.search.base import FallbackSearchProvider, SearchProvider, SearchProviderError


class _FailingProvider(SearchProvider):
    name = "failing"

    def search(self, query, max_results=10):
        raise SearchProviderError("simulated failure")


class _WorkingProvider(SearchProvider):
    name = "working"

    def search(self, query, max_results=10):
        return [{"title": "T", "url": "https://example.invalid/x", "snippet": None}]


class TestFallbackSearchProvider(unittest.TestCase):
    def test_falls_through_to_second_provider_on_first_failure(self):
        provider = FallbackSearchProvider([_FailingProvider(), _WorkingProvider()])
        results = provider.search("q")
        self.assertEqual(results[0]["url"], "https://example.invalid/x")

    def test_raises_when_every_provider_fails(self):
        provider = FallbackSearchProvider([_FailingProvider(), _FailingProvider()])
        with self.assertRaises(SearchProviderError):
            provider.search("q")

    def test_requires_at_least_one_provider(self):
        with self.assertRaises(ValueError):
            FallbackSearchProvider([])


if __name__ == "__main__":
    unittest.main()
