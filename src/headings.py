"""Extract headings from Markdown and compute GitHub-like slugs."""

import re
from pathlib import Path

ATX_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
HTML_ID = re.compile(r"""\bid=(["'])([^"']+)\1""", re.IGNORECASE)


def _strip_fenced_code(text: str) -> str:
    """Remove fenced code blocks so headings inside them are ignored."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_fence = False
    fence_char = ""
    for line in lines:
        stripped = line.lstrip()
        if not in_fence:
            m = re.match(r"^(```+|~~~+)", stripped)
            if m:
                in_fence = True
                fence_char = m.group(1)[0]
                result.append("\n" * (line.count("\n")))
                continue
            result.append(line)
        else:
            if stripped.startswith(fence_char * 3) and len(stripped) >= 3:
                in_fence = False
            result.append("\n" * (line.count("\n")))
    return "".join(result)


def _extract_html_ids(text: str) -> list[str]:
    """Return explicit HTML id values embedded in heading text."""
    return [match.group(2).lower() for match in HTML_ID.finditer(text)]


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags, keeping their text content."""
    return re.sub(r"<[^>]+>", "", text)


def _clean_heading_text(text: str) -> str:
    """Strip markdown emphasis and inline links from heading text."""
    text = _strip_html_tags(text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    # Only treat underscores as emphasis when not part of a word/identifier.
    text = re.sub(r"(?<![\w])_([^_]+)_(?![\w])", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    return text.strip()


def _slugify(text: str) -> str:
    """Convert heading text to a GitHub-like slug."""
    text = _clean_heading_text(text)
    text = text.lower()
    # GitHub keeps word chars, spaces, and hyphens; other punctuation is removed.
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = text.strip()
    # Each whitespace char becomes a hyphen (double spaces -> "--").
    text = re.sub(r"\s", "-", text)
    return text.strip("-")


def extract_heading_slugs(text: str) -> set[str]:
    """Return the set of slugs for all headings in *text*."""
    text = _strip_fenced_code(text)
    lines = text.splitlines()
    raw_headings: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = ATX_HEADING.match(line)
        if m:
            raw_headings.append(m.group(2))
            i += 1
            continue
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip() and re.match(r"^=+\s*$", next_line):
                raw_headings.append(line.strip())
                i += 2
                continue
            if next_line.strip() and re.match(r"^-+\s*$", next_line):
                raw_headings.append(line.strip())
                i += 2
                continue
        i += 1

    slug_counts: dict[str, int] = {}
    slugs: set[str] = set()
    for heading in raw_headings:
        for html_id in _extract_html_ids(heading):
            if html_id:
                slugs.add(html_id)

        base = _slugify(heading)
        if not base:
            continue
        count = slug_counts.get(base, 0)
        slug_counts[base] = count + 1
        if count == 0:
            slugs.add(base)
        else:
            slugs.add(f"{base}-{count}")
    return slugs


def load_heading_slugs(path: Path) -> set[str]:
    """Load heading slugs from a markdown file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return extract_heading_slugs(text)
