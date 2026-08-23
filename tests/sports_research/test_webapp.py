"""Basic smoke tests for the local web UI, using Flask's test client.
Only exercises the ambiguous-request path, which needs no network."""

import unittest

from sports_research.webapp import app


class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sports Research Agent", response.data)

    def test_ambiguous_query_shows_clarification_report_no_download_links(self):
        response = self.client.post("/research", data={"query": "Show me United's matches from last season."})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"needs clarification", response.data)
        self.assertNotIn(b"Download CSV", response.data)

    def test_empty_query_redirects_home(self):
        response = self.client.post("/research", data={"query": ""})
        self.assertEqual(response.status_code, 302)

    def test_download_unknown_run_id_is_404(self):
        response = self.client.get("/download/nonexistent/csv")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
