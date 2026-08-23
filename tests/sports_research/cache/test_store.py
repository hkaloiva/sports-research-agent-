import tempfile
import time
import unittest
from pathlib import Path

from sports_research.cache.store import CachedContentProvider, CachedSearchProvider, CacheStore


class TestCacheStore(unittest.TestCase):
    def test_get_returns_none_for_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(CacheStore(tmp).get("search", "q"))

    def test_set_then_get_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CacheStore(tmp)
            store.set("search", "q", [{"title": "T", "url": "https://example.invalid", "snippet": None}])
            self.assertEqual(store.get("search", "q")[0]["title"], "T")

    def test_expired_entry_is_not_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CacheStore(tmp, ttl_seconds=0)
            store.set("search", "q", ["x"])
            time.sleep(0.01)
            self.assertIsNone(store.get("search", "q"))

    def test_invalidate_removes_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CacheStore(tmp)
            store.set("content", "https://example.invalid", {"text": "hi"})
            store.invalidate("content", "https://example.invalid")
            self.assertIsNone(store.get("content", "https://example.invalid"))

    def test_clear_removes_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CacheStore(tmp)
            store.set("search", "a", [1])
            store.set("content", "b", [2])
            store.clear()
            self.assertIsNone(store.get("search", "a"))
            self.assertIsNone(store.get("content", "b"))


class TestCachedSearchProvider(unittest.TestCase):
    def test_second_call_does_not_hit_the_underlying_provider(self):
        calls = []

        class CountingProvider:
            name = "counting"

            def search(self, query, max_results=10):
                calls.append(query)
                return [{"title": "T", "url": "https://example.invalid", "snippet": None}]

        with tempfile.TemporaryDirectory() as tmp:
            provider = CachedSearchProvider(CountingProvider(), CacheStore(tmp))
            provider.search("q")
            provider.search("q")

        self.assertEqual(len(calls), 1)


class TestCachedContentProvider(unittest.TestCase):
    def test_a_failed_fetch_is_not_cached_so_it_can_be_retried(self):
        calls = []

        class FlakyProvider:
            name = "flaky"

            def fetch(self, url):
                calls.append(url)
                return {"url": url, "final_url": url, "http_status": None, "title": None, "text": None,
                         "retrieval_method": "flaky", "retrieved_at": "t", "error": "network error"}

        with tempfile.TemporaryDirectory() as tmp:
            provider = CachedContentProvider(FlakyProvider(), CacheStore(tmp))
            provider.fetch("https://example.invalid")
            provider.fetch("https://example.invalid")

        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
