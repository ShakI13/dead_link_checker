"""Tests for src.discover."""

import tempfile
import unittest
from pathlib import Path

from src.discover import discover_markdown_files


class DiscoverTests(unittest.TestCase):
    def test_finds_nested_md_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "top.md").write_text("# Top\n")
            sub = root / "docs" / "nested"
            sub.mkdir(parents=True)
            (sub / "inner.md").write_text("# Inner\n")

            found = discover_markdown_files(root)
            names = [p.name for p in found]
            self.assertEqual(names, ["inner.md", "top.md"])

    def test_skips_ignored_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.md").write_text("# OK\n")
            for skip in (".git", "venv", "node_modules", "__pycache__"):
                d = root / skip
                d.mkdir()
                (d / "hidden.md").write_text("# Hidden\n")

            found = discover_markdown_files(root)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].name, "ok.md")


if __name__ == "__main__":
    unittest.main()
