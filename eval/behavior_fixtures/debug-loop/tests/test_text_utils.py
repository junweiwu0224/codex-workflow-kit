import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from text_utils import canonical_slug  # noqa: E402


class CanonicalSlugTests(unittest.TestCase):
    def test_normalizes_case_and_outer_space(self):
        self.assertEqual(canonical_slug("  Launch Plan  "), "launch-plan")

    def test_collapses_runs_of_inner_whitespace(self):
        self.assertEqual(canonical_slug("Checkout   Summary"), "checkout-summary")

    def test_tabs_are_treated_as_word_separators(self):
        self.assertEqual(canonical_slug("Release\tNotes"), "release-notes")


if __name__ == "__main__":
    unittest.main()
