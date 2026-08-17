"""Check local file/directory targets and heading fragments."""

from dataclasses import dataclass
from pathlib import Path

from src.headings import load_heading_slugs
from src.resolve import ResolvedLink


@dataclass
class LocalCheckResult:
    broken: bool
    status: str | None = None
    warning: str | None = None


def check_local(resolved: ResolvedLink) -> LocalCheckResult:
    """Verify local path exists and optional heading fragment is present."""
    path = resolved.local_path
    if path is None:
        return LocalCheckResult(broken=True, status="missing file")

    if path.exists():
        if resolved.fragment is not None:
            warning = _check_heading(path, resolved.fragment)
            if warning:
                return LocalCheckResult(broken=False, warning=warning)
        return LocalCheckResult(broken=False)

    return LocalCheckResult(broken=True, status="missing file")


def _check_heading(path: Path, fragment: str) -> str | None:
    """Return warning message if heading slug is missing."""
    if path.is_dir():
        return None
    if path.suffix.lower() != ".md":
        return None

    slugs = load_heading_slugs(path)
    normalized = fragment.lower()
    if normalized not in slugs:
        return fragment
    return None
