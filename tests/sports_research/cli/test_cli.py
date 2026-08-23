"""CLI tests via subprocess. Only exercises paths that don't require live
network access (an ambiguous request returns before searching) — see
tests/live/ for the network-dependent smoke tests."""

import subprocess
import sys
import unittest

from config import BASE_DIR


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "sports_research.cli", *args],
        capture_output=True, text=True, cwd=BASE_DIR, timeout=30,
    )


class TestCLI(unittest.TestCase):
    def test_help_runs_without_error(self):
        proc = _run_cli("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("QUERY", proc.stdout.upper())

    def test_ambiguous_query_reports_clarification_and_exits_nonzero(self):
        proc = _run_cli("Show me United's matches from last season.")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("needs clarification", proc.stdout)
        self.assertIn("Which club named 'United'", proc.stdout)

    def test_stage_progress_is_shown(self):
        proc = _run_cli("Show me United's matches from last season.")
        self.assertIn("[1/8] Understanding request", proc.stdout)


if __name__ == "__main__":
    unittest.main()
