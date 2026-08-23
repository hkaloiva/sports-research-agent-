"""Mocks the ddgs library — no live network access."""

import unittest
from unittest.mock import MagicMock, patch

from sports_research.search.base import SearchProviderError
from sports_research.search.duckduckgo_provider import DuckDuckGoSearchProvider


class TestDuckDuckGoSearchProvider(unittest.TestCase):
    @patch("ddgs.DDGS")
    def test_returns_hits_shaped_for_search_module(self, mock_ddgs_class):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.text.return_value = [
            {"title": "Arsenal 2003-04 season", "href": "https://en.wikipedia.org/wiki/X", "body": "a snippet"},
            {"title": "No snippet here", "href": "https://example.invalid/y", "body": ""},
        ]
        mock_ddgs_class.return_value = mock_client

        provider = DuckDuckGoSearchProvider()
        results = provider.search("arsenal 2003/04", max_results=5)

        self.assertEqual(results[0], {"title": "Arsenal 2003-04 season", "url": "https://en.wikipedia.org/wiki/X", "snippet": "a snippet"})
        self.assertIsNone(results[1]["snippet"])
        mock_client.text.assert_called_once_with("arsenal 2003/04", max_results=5)

    @patch("ddgs.DDGS")
    def test_hit_missing_title_or_url_is_skipped_not_fabricated(self, mock_ddgs_class):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.text.return_value = [{"title": "", "href": "https://example.invalid/z", "body": None}]
        mock_ddgs_class.return_value = mock_client

        provider = DuckDuckGoSearchProvider()
        self.assertEqual(provider.search("q"), [])

    @patch("ddgs.DDGS")
    def test_wraps_library_exceptions_as_search_provider_error(self, mock_ddgs_class):
        mock_ddgs_class.side_effect = RuntimeError("network down")
        provider = DuckDuckGoSearchProvider()
        with self.assertRaises(SearchProviderError):
            provider.search("q")


if __name__ == "__main__":
    unittest.main()
