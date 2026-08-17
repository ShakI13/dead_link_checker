"""Discover Markdown files under a directory tree."""

from pathlib import Path

SKIP_DIRS = {".git", "venv", "node_modules", "__pycache__"}


def discover_markdown_files(root: Path) -> list[Path]:
    """Return sorted list of .md files under *root*, skipping ignored directories."""
    root = root.resolve()
    found: list[Path] = []

    def walk(directory: Path) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in SKIP_DIRS:
                    continue
                walk(entry)
            elif entry.is_file() and entry.suffix.lower() == ".md":
                found.append(entry.resolve())

    walk(root)
    return sorted(found)
