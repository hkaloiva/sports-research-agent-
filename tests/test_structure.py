"""Sanity checks that the expected project scaffolding exists."""

import unittest

from config import BASE_DIR, DATA_DIR, DOCS_DIR, EXPORTS_DIR, PROCESSED_DIR, RAW_DIR


class TestProjectStructure(unittest.TestCase):
    def test_top_level_dirs_exist(self):
        for path in (DATA_DIR, DOCS_DIR, BASE_DIR / "tests"):
            self.assertTrue(path.is_dir(), f"missing directory: {path}")

    def test_data_subdirs_exist(self):
        for path in (RAW_DIR, PROCESSED_DIR, EXPORTS_DIR):
            self.assertTrue(path.is_dir(), f"missing directory: {path}")

    def test_readme_exists(self):
        self.assertTrue((BASE_DIR / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()
