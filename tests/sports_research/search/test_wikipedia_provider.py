import unittest
from unittest.mock import MagicMock, patch

import requests

from sports_research.search.base import SearchProviderError
from sports_research.search.wikipedia_provider import WikipediaSearchProvider


class TestWikipediaSearchProvider(unittest.TestCase):
    @patch("requests.get")
    def test_parses_search_results_into_wiki_urls(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            "query": {"search": [{"title": "2003–04 FA Premier League", "snippet": "some <span>highlighted</span> text"}]}
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        provider = WikipediaSearchProvider()
        results = provider.search("premier league 2003 04")

        self.assertEqual(results[0]["url"], "https://en.wikipedia.org/wiki/2003–04_FA_Premier_League")
        self.assertEqual(results[0]["title"], "2003–04 FA Premier League")
        self.assertIn("highlighted", results[0]["snippet"])

    @patch("requests.get")
    def test_sends_a_real_user_agent(self, mock_get):
        response = MagicMock()
        response.json.return_value = {"query": {"search": []}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        WikipediaSearchProvider().search("q")

        _, kwargs = mock_get.call_args
        self.assertIn("User-Agent", kwargs["headers"])
        self.assertNotEqual(kwargs["headers"]["User-Agent"], "")

    @patch("requests.get")
    def test_network_error_raises_search_provider_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("timeout")
        with self.assertRaises(SearchProviderError):
            WikipediaSearchProvider().search("q")


if __name__ == "__main__":
    unittest.main()
