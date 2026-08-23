import unittest
from unittest.mock import patch

from sports_research.retrieval.browser_provider import BrowserContentProvider, browser_available


class TestBrowserAvailability(unittest.TestCase):
    def test_unavailable_without_playwright_never_raises(self):
        with patch.dict("sys.modules", {"playwright.sync_api": None}):
            self.assertFalse(browser_available())

    def test_fetch_reports_missing_dependency_rather_than_crashing(self):
        with patch.dict("sys.modules", {"playwright.sync_api": None}):
            content = BrowserContentProvider().fetch("https://example.invalid/x")
        self.assertIsNone(content["text"])
        self.assertIsNotNone(content["error"])


if __name__ == "__main__":
    unittest.main()
