"""Validates the ResearchRequest schema and examples, and confirms the
five required test concerns from Step 4: valid requests are accepted,
invalid requests are rejected, missing required information is
detected, ambiguous requests require clarification, and inferred values
are distinguishable from explicitly supplied ones."""

import copy
import json
import unittest

from config import BASE_DIR
from validation import build_request_validator, validate_request

EXAMPLES_DIR = BASE_DIR / "schema" / "examples" / "research_requests"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text())


class TestValidRequestsAreAccepted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = build_request_validator()

    def test_examples_exist(self):
        self.assertEqual(len(list(EXAMPLES_DIR.glob("*.json"))), 5)

    def test_all_five_examples_validate(self):
        for example_path in sorted(EXAMPLES_DIR.glob("*.json")):
            with self.subTest(example=example_path.name):
                request = json.loads(example_path.read_text())
                problems = validate_request(request, self.validator)
                self.assertEqual(problems, [])


class TestInvalidRequestsAreRejected(unittest.TestCase):
    """Deliberately break a known-good request in one way at a time."""

    @classmethod
    def setUpClass(cls):
        cls.validator = build_request_validator()

    def _good(self) -> dict:
        return copy.deepcopy(_load("01_team_season.json"))

    def test_rejects_ready_status_with_pending_clarifications(self):
        request = self._good()
        request["clarifications_needed"] = [{"field": "x", "question": "q", "reason": "r"}]
        self.assertTrue(validate_request(request, self.validator))

    def test_rejects_needs_clarification_status_with_no_clarifications(self):
        request = self._good()
        request["status"] = "needs_clarification"
        self.assertTrue(validate_request(request, self.validator))

    def test_rejects_inferred_value_without_a_basis(self):
        request = self._good()
        del request["constraints"]["sport"]["basis"]
        self.assertTrue(validate_request(request, self.validator))

    def test_rejects_explicit_value_carrying_a_basis(self):
        request = self._good()
        request["constraints"]["competition"]["basis"] = "should not be here"
        self.assertTrue(validate_request(request, self.validator))

    def test_rejects_unknown_constraint_field(self):
        request = self._good()
        request["constraints"]["made_up_field"] = {"value": "x", "source": "explicit"}
        self.assertTrue(validate_request(request, self.validator))

    def test_rejects_required_fields_entry_outside_result_record_vocabulary(self):
        request = self._good()
        request["constraints"]["required_fields"]["value"] = ["not_a_real_field"]
        self.assertTrue(validate_request(request, self.validator))

    def test_rejects_missing_raw_query(self):
        request = self._good()
        del request["raw_query"]
        self.assertTrue(validate_request(request, self.validator))


class TestMissingInformationIsDetected(unittest.TestCase):
    def setUp(self):
        self.request = _load("05_ambiguous_needs_clarification.json")

    def test_ambiguous_team_is_flagged_not_guessed(self):
        self.assertNotIn("teams", self.request["constraints"])
        fields = {c["field"] for c in self.request["clarifications_needed"]}
        self.assertIn("teams", fields)

    def test_ambiguous_season_is_flagged_not_guessed(self):
        self.assertNotIn("season", self.request["constraints"])
        fields = {c["field"] for c in self.request["clarifications_needed"]}
        self.assertIn("season", fields)


class TestAmbiguousRequestsRequireClarification(unittest.TestCase):
    def test_ambiguous_example_has_needs_clarification_status(self):
        request = _load("05_ambiguous_needs_clarification.json")
        self.assertEqual(request["status"], "needs_clarification")
        self.assertGreaterEqual(len(request["clarifications_needed"]), 1)

    def test_unambiguous_examples_are_ready_with_no_clarifications(self):
        for name in (
            "01_team_season.json",
            "02_head_to_head.json",
            "03_competition_date_range.json",
            "04_result_type_filter.json",
        ):
            with self.subTest(example=name):
                request = _load(name)
                self.assertEqual(request["status"], "ready")
                self.assertEqual(request["clarifications_needed"], [])


class TestInferredValuesAreDistinguishableFromExplicit(unittest.TestCase):
    def test_team_season_example_marks_sport_inferred_and_teams_explicit(self):
        request = _load("01_team_season.json")
        self.assertEqual(request["constraints"]["sport"]["source"], "inferred")
        self.assertIn("basis", request["constraints"]["sport"])
        self.assertEqual(request["constraints"]["teams"]["source"], "explicit")
        self.assertNotIn("basis", request["constraints"]["teams"])

    def test_season_normalization_keeps_source_explicit_but_keeps_raw_text(self):
        request = _load("01_team_season.json")
        season = request["constraints"]["season"]
        self.assertEqual(season["source"], "explicit")
        self.assertEqual(season["value"], "2003-2004")
        self.assertEqual(season["raw_value"], "2003/04")

    def test_every_inferred_constraint_across_all_examples_carries_a_basis(self):
        for example_path in sorted(EXAMPLES_DIR.glob("*.json")):
            request = json.loads(example_path.read_text())
            for field, entry in request["constraints"].items():
                with self.subTest(example=example_path.name, field=field):
                    if entry["source"] == "inferred":
                        self.assertIn("basis", entry)
                    else:
                        self.assertNotIn("basis", entry)


if __name__ == "__main__":
    unittest.main()
