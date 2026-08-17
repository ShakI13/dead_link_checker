"""Tests for src.headings."""

import unittest

from src.headings import extract_heading_slugs


class HeadingsTests(unittest.TestCase):
    def test_basic_slug(self) -> None:
        text = "# Hello World\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("hello-world", slugs)

    def test_duplicate_headings_get_suffix(self) -> None:
        text = "## Foo bar\n\n## Foo bar\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("foo-bar", slugs)
        self.assertIn("foo-bar-1", slugs)

    def test_underscore_preserved(self) -> None:
        text = "## A_B\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("a_b", slugs)

    def test_ignores_headings_in_fenced_code(self) -> None:
        text = "```\n# Not A Heading\n```\n# Real Heading\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("real-heading", slugs)
        self.assertNotIn("not-a-heading", slugs)

    def test_html_id_anchor(self) -> None:
        text = '## <a id="migrations-politic">Policy</a>\n'
        slugs = extract_heading_slugs(text)
        self.assertIn("migrations-politic", slugs)

    def test_ampersand_produces_double_hyphen(self) -> None:
        text = "## Data Fetching & State Management\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("data-fetching--state-management", slugs)

    def test_slash_produces_double_hyphen(self) -> None:
        text = "## 8. Auth / Token\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("8-auth--token", slugs)

    def test_underscores_in_identifiers_preserved(self) -> None:
        text = "### 0001_create_tmp_table\n"
        slugs = extract_heading_slugs(text)
        self.assertIn("0001_create_tmp_table", slugs)


if __name__ == "__main__":
    unittest.main()
