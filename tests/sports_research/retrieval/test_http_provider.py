import unittest
from unittest.mock import MagicMock, patch

import requests

from sports_research.retrieval import http_provider
from sports_research.retrieval.http_provider import HTTPContentProvider, extract_main_text


class TestExtractMainText(unittest.TestCase):
    def test_strips_boilerplate_tags(self):
        html = "<html><head><title>Page Title</title></head><body><nav>skip</nav><p>Real content</p><footer>skip</footer></body></html>"
        title, text = extract_main_text(html)
        self.assertEqual(title, "Page Title")
        self.assertIn("Real content", text)
        self.assertNotIn("skip", text)


class TestHTTPContentProvider(unittest.TestCase):
    def setUp(self):
        http_provider._robots_cache.clear()

    @patch("sports_research.retrieval.http_provider._robots_allows", return_value=True)
    @patch("requests.get")
    def test_successful_fetch_captures_all_required_fields(self, mock_get, _mock_robots):
        response = MagicMock()
        response.status_code = 200
        response.url = "https://example.invalid/final"
        response.headers = {"Content-Type": "text/html"}
        response.text = "<html><head><title>T</title></head><body><p>hello</p></body></html>"
        mock_get.return_value = response

        content = HTTPContentProvider().fetch("https://example.invalid/start")

        self.assertEqual(content["url"], "https://example.invalid/start")
        self.assertEqual(content["final_url"], "https://example.invalid/final")
        self.assertEqual(content["http_status"], 200)
        self.assertEqual(content["title"], "T")
        self.assertIn("hello", content["text"])
        self.assertEqual(content["retrieval_method"], "http")
        self.assertIsNotNone(content["retrieved_at"])
        self.assertIsNone(content["error"])

    @patch("sports_research.retrieval.http_provider._robots_allows", return_value=True)
    @patch("requests.get")
    def test_http_error_status_is_recorded_not_raised(self, mock_get, _mock_robots):
        response = MagicMock()
        response.status_code = 404
        response.url = "https://example.invalid/missing"
        mock_get.return_value = response

        content = HTTPContentProvider().fetch("https://example.invalid/missing")

        self.assertEqual(content["http_status"], 404)
        self.assertIsNone(content["text"])
        self.assertIn("404", content["error"])

    @patch("sports_research.retrieval.http_provider._robots_allows", return_value=True)
    @patch("requests.get")
    def test_network_failure_is_recorded_not_raised(self, mock_get, _mock_robots):
        mock_get.side_effect = requests.RequestException("connection refused")
        content = HTTPContentProvider().fetch("https://example.invalid/x")
        self.assertIsNone(content["http_status"])
        self.assertIn("connection refused", content["error"])

    @patch("sports_research.retrieval.http_provider._robots_allows", return_value=False)
    def test_robots_disallowed_url_is_never_fetched(self, _mock_robots):
        with patch("requests.get") as mock_get:
            content = HTTPContentProvider().fetch("https://example.invalid/disallowed")
            mock_get.assert_not_called()
        self.assertIn("robots.txt", content["error"])

    @patch("sports_research.retrieval.http_provider._robots_allows", return_value=True)
    @patch("requests.get")
    def test_never_claims_a_source_was_read_when_content_type_unsupported(self, mock_get, _mock_robots):
        response = MagicMock()
        response.status_code = 200
        response.url = "https://example.invalid/data.pdf"
        response.headers = {"Content-Type": "application/pdf"}
        mock_get.return_value = response

        content = HTTPContentProvider().fetch("https://example.invalid/data.pdf")
        self.assertIsNone(content["text"])
        self.assertIn("content-type", content["error"])


if __name__ == "__main__":
    unittest.main()
