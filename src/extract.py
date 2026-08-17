"""Extract links from Markdown documents."""

import re
from dataclasses import dataclass

AUTO_LINK = re.compile(r"<(https?://[^>]+)>")
REF_DEF = re.compile(r"^\s*\[([^\]]+)\]:\s+(\S+)", re.MULTILINE)
REF_USAGE = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")
SHORTCUT = re.compile(r"(?<!\!)\[([^\]]+)\](?!\[|\(|:)")
BARE_URL = re.compile(r"(?<![\"'=])https?://[^\s<>\"]+")
HTML_LINK = re.compile(
    r"""<a\s+[^>]*href\s*=\s*(["'])(.*?)\1""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedLink:
    text: str
    url: str
    line: int


def _strip_ignored_regions(text: str) -> str:
    """Replace fenced code blocks and inline code with spaces (preserve length/lines)."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_fence = False
    fence_char = ""

    for line in lines:
        if not in_fence:
            # Check for fence start
            stripped = line.lstrip()
            m = re.match(r"^(```+|~~~+)", stripped)
            if m:
                in_fence = True
                fence_char = m.group(1)[0]
                result.append(" " * len(line))
                continue
            # Strip inline code on this line
            cleaned = _strip_inline_code(line)
            result.append(cleaned)
        else:
            if line.lstrip().startswith(fence_char * 3):
                in_fence = False
            result.append(" " * len(line))

    return "".join(result)


def _strip_inline_code(line: str) -> str:
    """Replace inline code spans with spaces."""
    result: list[str] = []
    i = 0
    while i < len(line):
        if line[i] == "`":
            # Find closing backtick
            j = i + 1
            while j < len(line) and line[j] != "`":
                j += 1
            if j < len(line):
                result.append(" " * (j - i + 1))
                i = j + 1
                continue
        result.append(line[i])
        i += 1
    return "".join(result)


def _parse_destination(raw: str) -> str:
    """Extract URL from a link destination, handling optional title."""
    raw = raw.strip()
    if raw.startswith("<"):
        end = raw.find(">")
        if end != -1:
            return raw[1:end].strip()
        return raw
    # Split off optional title in quotes
    if " " in raw:
        url_part = raw.split(None, 1)[0]
        return url_part.strip()
    return raw


def _trim_bare_url(url: str) -> str:
    """Trim trailing punctuation from bare URLs."""
    return url.rstrip(".,;:!?)")


def _normalize_ref_id(ref_id: str) -> str:
    return ref_id.strip().casefold()


def _parse_inline_link(text: str, pos: int) -> tuple[int, int, str, str] | None:
    """Parse ``[text](url)`` or ``![alt](url)`` starting at *pos*."""
    if pos >= len(text):
        return None

    if text.startswith("![", pos):
        i = pos + 2
    elif text[pos] == "[":
        i = pos + 1
    else:
        return None

    text_parts: list[str] = []
    depth = 1
    while i < len(text) and depth > 0:
        if text.startswith("![", i) or text[i] == "[":
            nested = _parse_inline_link(text, i)
            if nested is not None:
                text_parts.append(nested[2])
                i = nested[1]
                continue
        if text[i] == "]":
            depth -= 1
            if depth == 0:
                i += 1
                break
            text_parts.append(text[i])
            i += 1
        else:
            text_parts.append(text[i])
            i += 1
    else:
        return None

    if i >= len(text) or text[i] != "(":
        return None

    i += 1
    dest_start = i
    paren_depth = 1
    while i < len(text) and paren_depth > 0:
        if text[i] == "(":
            paren_depth += 1
        elif text[i] == ")":
            paren_depth -= 1
            if paren_depth == 0:
                dest = _parse_destination(text[dest_start:i])
                return pos, i + 1, "".join(text_parts), dest
        i += 1
    return None


def _find_inline_links(text: str) -> list[tuple[int, int, str, str]]:
    """Find inline/image links, including nested links such as badge buttons."""
    results: list[tuple[int, int, str, str]] = []

    def parse_at(pos: int) -> tuple[int, int, str, str] | None:
        link = _parse_inline_link(text, pos)
        if link is None:
            return None
        results.append(link)
        start, end, _, _ = link
        scan = start + (2 if text.startswith("![", start) else 1)
        while scan < end:
            if text.startswith("![", scan) or text[scan] == "[":
                nested = parse_at(scan)
                if nested is not None:
                    scan = nested[1]
                    continue
            scan += 1
        return link

    i = 0
    while i < len(text):
        if text.startswith("![", i) or text[i] == "[":
            link = parse_at(i)
            if link is not None:
                i = link[1]
                continue
        i += 1

    return results


def extract_links(text: str) -> list[ExtractedLink]:
    """Extract all links from markdown *text*."""
    cleaned = _strip_ignored_regions(text)
    lines = cleaned.splitlines()

    # Build reference definitions from cleaned text (ignore code regions)
    ref_defs: dict[str, str] = {}
    for m in REF_DEF.finditer(cleaned):
        ref_id = _normalize_ref_id(m.group(1))
        url = _parse_destination(m.group(2))
        ref_defs[ref_id] = url

    seen: set[tuple[int, str]] = set()
    links: list[ExtractedLink] = []
    captured_spans: list[tuple[int, int]] = []

    def add(text: str, url: str, line: int, span: tuple[int, int] | None = None) -> None:
        if span is not None:
            captured_spans.append(span)
        key = (line, url)
        if key not in seen:
            seen.add(key)
            links.append(ExtractedLink(text=text, url=url, line=line))

    def line_at(pos: int) -> int:
        return text[:pos].count("\n") + 1

    def _overlaps(start: int, end: int) -> bool:
        for span_start, span_end in captured_spans:
            if start < span_end and span_start < end:
                return True
        return False

    # Inline and image links (including nested badge links)
    for start, end, text_part, dest in _find_inline_links(cleaned):
        add(text_part, dest, line_at(start), (start, end))

    # Autolinks
    for m in AUTO_LINK.finditer(cleaned):
        add(m.group(1), m.group(1), line_at(m.start()), m.span())

    # Reference usage [text][id]
    for m in REF_USAGE.finditer(cleaned):
        text_part = m.group(1)
        ref_id = m.group(2)
        if not ref_id:
            ref_id = text_part
        norm = _normalize_ref_id(ref_id)
        if norm in ref_defs:
            add(text_part, ref_defs[norm], line_at(m.start()), m.span())

    # Shortcut references [text] when definition exists
    for m in SHORTCUT.finditer(cleaned):
        text_part = m.group(1)
        norm = _normalize_ref_id(text_part)
        if norm in ref_defs:
            add(text_part, ref_defs[norm], line_at(m.start()), m.span())

    # HTML links
    for m in HTML_LINK.finditer(cleaned):
        add(m.group(2), m.group(2), line_at(m.start()), m.span())

    # Bare URLs (not already captured)
    for m in BARE_URL.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        url = _trim_bare_url(m.group(0))
        add(url, url, line_at(m.start()), m.span())

    return links
