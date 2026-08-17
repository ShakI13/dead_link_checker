"""Tests for check_links CLI helpers."""

import tempfile
import unittest
from pathlib import Path

from check_links import path_for_report


class PathForReportTests(unittest.TestCase):
    def test_nested_file_is_relative_to_scan_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "docs" / "page.md"
            nested.parent.mkdir()
            nested.write_text("# Page\n")
            self.assertEqual(path_for_report(nested, root), "docs/page.md")

    def test_does_not_use_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "README.md"
            target.write_text("# Readme\n")
            reported = path_for_report(target, root)
            self.assertEqual(reported, "README.md")
            self.assertFalse(Path(reported).is_absolute())


if __name__ == "__main__":
    unittest.main()
