"""Classify and resolve extracted URLs."""

import posixpath
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from urllib.parse import unquote, urlparse


class LinkKind(Enum):
    SKIP = auto()
    HTTP = auto()
    LOCAL = auto()
    BROKEN = auto()


@dataclass
class ResolvedLink:
    kind: LinkKind
    url: str
    local_path: Path | None = None
    fragment: str | None = None
    status: str | None = None  # for BROKEN kind


SKIP_SCHEMES = {"mailto", "tel", "data"}


def classify_and_resolve(url: str, source_md: Path) -> ResolvedLink:
    """Classify *url* and resolve local paths relative to *source_md*."""
    url = url.strip()
    if not url:
        return ResolvedLink(kind=LinkKind.BROKEN, url=url, status="empty url")

    try:
        parsed = urlparse(url)
    except ValueError:
        return ResolvedLink(kind=LinkKind.BROKEN, url=url, status="invalid url")
    scheme = parsed.scheme.lower()

    if scheme in SKIP_SCHEMES:
        return ResolvedLink(kind=LinkKind.SKIP, url=url)

    if scheme and scheme not in ("http", "https", "file", ""):
        return ResolvedLink(kind=LinkKind.SKIP, url=url)

    if scheme in ("http", "https"):
        return ResolvedLink(kind=LinkKind.HTTP, url=url)

    if url.startswith("//"):
        return ResolvedLink(kind=LinkKind.HTTP, url=f"https:{url}")

    if scheme == "file":
        path_str = unquote(parsed.path)
        local = Path(path_str)
        fragment = unquote(parsed.fragment) if parsed.fragment else None
        return ResolvedLink(
            kind=LinkKind.LOCAL, url=url, local_path=local, fragment=fragment
        )

    # Fragment-only link
    if url.startswith("#"):
        fragment = unquote(url[1:])
        return ResolvedLink(
            kind=LinkKind.LOCAL,
            url=url,
            local_path=source_md.resolve(),
            fragment=fragment,
        )

    # Local path (relative or absolute)
    fragment = None
    path_part = url
    if "#" in path_part:
        path_part, frag = path_part.split("#", 1)
        fragment = unquote(frag)
    if "?" in path_part:
        path_part = path_part.split("?", 1)[0]

    path_part = unquote(path_part)

    if posixpath.isabs(path_part):
        local = Path(path_part).resolve()
    else:
        local = (source_md.parent / path_part).resolve()

    return ResolvedLink(
        kind=LinkKind.LOCAL, url=url, local_path=local, fragment=fragment
    )
