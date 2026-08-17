"""Tests for src.check_local."""

import tempfile
import unittest
from pathlib import Path

from src.check_local import check_local
from src.resolve import LinkKind, ResolvedLink


class CheckLocalTests(unittest.TestCase):
    def test_missing_file_is_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resolved = ResolvedLink(
                kind=LinkKind.LOCAL,
                url="missing.md",
                local_path=Path(tmp) / "missing.md",
            )
            result = check_local(resolved)
            self.assertTrue(result.broken)
            self.assertEqual(result.status, "missing file")

    def test_existing_directory_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resolved = ResolvedLink(
                kind=LinkKind.LOCAL,
                url="docs/",
                local_path=Path(tmp),
            )
            result = check_local(resolved)
            self.assertFalse(result.broken)
            self.assertIsNone(result.warning)

    def test_existing_file_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "exists.md"
            target.write_text("# Exists\n")
            resolved = ResolvedLink(
                kind=LinkKind.LOCAL,
                url="exists.md",
                local_path=target,
            )
            result = check_local(resolved)
            self.assertFalse(result.broken)

    def test_missing_heading_is_warning_not_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "page.md"
            target.write_text("# Real Section\n")
            resolved = ResolvedLink(
                kind=LinkKind.LOCAL,
                url="page.md#missing-section",
                local_path=target,
                fragment="missing-section",
            )
            result = check_local(resolved)
            self.assertFalse(result.broken)
            self.assertEqual(result.warning, "missing-section")


if __name__ == "__main__":
    unittest.main()
