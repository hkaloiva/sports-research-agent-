import unittest
from unittest.mock import patch

from sports_research.extraction.engine import ExtractionEngine

CONTEXT = dict(sport="football", competition="Premier League", season="2003-2004",
               source="s", source_url="https://example.invalid", source_accessed_at="2026-08-23T12:00:00Z")


class TestExtractionEngineDeterministicOnly(unittest.TestCase):
    def test_uses_deterministic_extraction_when_llm_disabled(self):
        engine = ExtractionEngine(use_local_llm=False)
        outcome = engine.extract_two_participant("2003-08-16:\nArsenal 2-1 Everton\n", **CONTEXT)
        self.assertEqual(len(outcome.records), 1)
        self.assertFalse(outcome.used_local_llm)


class TestExtractionEngineLocalLLMGracefulDegradation(unittest.TestCase):
    @patch("sports_research.extraction.local_llm.ollama_available", return_value=False)
    def test_never_crashes_when_ollama_is_unavailable(self, _mock_available):
        engine = ExtractionEngine(use_local_llm=True)
        outcome = engine.extract_two_participant("no matches in this text", **CONTEXT)
        self.assertEqual(outcome.records, [])
        self.assertIn("no Ollama server is reachable", outcome.capability_note)

    @patch("sports_research.extraction.local_llm.OptionalLocalLLMExtractor.extract_raw")
    @patch("sports_research.extraction.local_llm.ollama_available", return_value=True)
    def test_uses_llm_only_when_deterministic_finds_nothing(self, _mock_available, mock_extract_raw):
        mock_extract_raw.return_value = "2003-08-16:\nArsenal 2-1 Everton\n"
        engine = ExtractionEngine(use_local_llm=True)
        outcome = engine.extract_two_participant("unstructured prose the regex can't parse", **CONTEXT)
        self.assertTrue(outcome.used_local_llm)
        self.assertEqual(len(outcome.records), 1)
        mock_extract_raw.assert_called_once()

    @patch("sports_research.extraction.local_llm.ollama_available", return_value=True)
    def test_does_not_call_llm_when_deterministic_already_found_records(self, mock_available):
        engine = ExtractionEngine(use_local_llm=True)
        outcome = engine.extract_two_participant("2003-08-16:\nArsenal 2-1 Everton\n", **CONTEXT)
        self.assertFalse(outcome.used_local_llm)
        # ollama_available() should not even need to be checked in this path
        mock_available.assert_not_called()


if __name__ == "__main__":
    unittest.main()
