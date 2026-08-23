"""Regression checks that the example records validate against the schema."""

import json
import unittest

from config import BASE_DIR
from validation import build_validator, load_schema, validate_record

EXAMPLES_DIR = BASE_DIR / "schema" / "examples"


class TestResultRecordSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()
        cls.validator = build_validator()

    def test_examples_exist(self):
        examples = list(EXAMPLES_DIR.glob("*.json"))
        self.assertEqual(len(examples), 3)

    def test_all_examples_validate(self):
        for example_path in sorted(EXAMPLES_DIR.glob("*.json")):
            with self.subTest(example=example_path.name):
                record = json.loads(example_path.read_text())
                problems = validate_record(record, self.validator)
                self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
