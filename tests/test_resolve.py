"""Tests for src.resolve."""

import tempfile
import unittest
from pathlib import Path

from src.resolve import LinkKind, classify_and_resolve


class ResolveTests(unittest.TestCase):
    def test_relative_path_from_source_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub = root / "docs"
            sub.mkdir()
            source = sub / "page.md"
            target = root / "other.md"
            target.write_text("# Other\n")
            resolved = classify_and_resolve("../other.md", source)
            self.assertEqual(resolved.kind, LinkKind.LOCAL)
            assert resolved.local_path is not None
            self.assertTrue(resolved.local_path.exists())

    def test_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "abs.md"
            target.write_text("# Abs\n")
            resolved = classify_and_resolve(str(target), Path("/any/doc.md"))
            self.assertEqual(resolved.kind, LinkKind.LOCAL)
            assert resolved.local_path is not None
            self.assertEqual(resolved.local_path, target.resolve())

    def test_file_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file_target.md"
            target.write_text("# File\n")
            url = target.as_uri()
            resolved = classify_and_resolve(url, Path("/any/doc.md"))
            self.assertEqual(resolved.kind, LinkKind.LOCAL)
            assert resolved.local_path is not None
            self.assertTrue(resolved.local_path.exists())

    def test_fragment_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "page.md"
            source.write_text("# Title\n")
            resolved = classify_and_resolve("#title", source)
            self.assertEqual(resolved.kind, LinkKind.LOCAL)
            assert resolved.local_path is not None
            self.assertEqual(resolved.local_path, source.resolve())
            self.assertEqual(resolved.fragment, "title")

    def test_empty_url_is_broken(self) -> None:
        resolved = classify_and_resolve("  ", Path("/tmp/doc.md"))
        self.assertEqual(resolved.kind, LinkKind.BROKEN)

    def test_malformed_url_is_broken_not_crash(self) -> None:
        resolved = classify_and_resolve(
            "https://example.com](https://example.com", Path("/tmp/doc.md")
        )
        self.assertEqual(resolved.kind, LinkKind.BROKEN)
        self.assertEqual(resolved.status, "invalid url")


if __name__ == "__main__":
    unittest.main()
