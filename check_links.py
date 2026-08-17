#!/usr/bin/env python3
"""CLI entry point for the Markdown link checker."""

import argparse
import sys
from pathlib import Path

from src.check_http import HttpChecker
from src.check_local import check_local
from src.discover import discover_markdown_files
from src.extract import extract_links
from src.report import BrokenLink, HeadingWarning, print_report
from src.resolve import LinkKind, classify_and_resolve


def path_for_report(md_path: Path, scan_root: Path) -> str:
    """Return *md_path* relative to *scan_root* (POSIX), never an absolute home path."""
    resolved_file = md_path.resolve()
    resolved_root = scan_root.resolve()
    try:
        return resolved_file.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_file.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check links in Markdown files under a directory."
    )
    parser.add_argument(
        "path",
        help="Directory to scan (must exist and be a directory)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10)",
    )
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        print("error: --timeout must be greater than 0", file=sys.stderr)
        return 2

    scan_root = Path(args.path)
    if not scan_root.exists():
        print(f"error: path does not exist: {scan_root}", file=sys.stderr)
        return 2
    if not scan_root.is_dir():
        print(f"error: path is not a directory: {scan_root}", file=sys.stderr)
        return 2
    scan_root = scan_root.resolve()

    md_files = discover_markdown_files(scan_root)
    http_checker = HttpChecker(timeout=args.timeout)

    broken: list[BrokenLink] = []
    warnings: list[HeadingWarning] = []
    checked_urls: set[str] = set()

    for md_path in md_files:
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(
                f"warning: skipping non-UTF-8 file: {path_for_report(md_path, scan_root)}",
                file=sys.stderr,
            )
            continue
        except OSError as exc:
            print(
                f"warning: cannot read {path_for_report(md_path, scan_root)}: {exc}",
                file=sys.stderr,
            )
            continue

        rel_file = path_for_report(md_path, scan_root)
        for link in extract_links(text):
            resolved = classify_and_resolve(link.url, md_path)

            if resolved.kind == LinkKind.SKIP:
                continue

            if resolved.kind == LinkKind.BROKEN:
                broken.append(
                    BrokenLink(
                        file=rel_file,
                        line=link.line,
                        text=link.text,
                        url=link.url,
                        status=resolved.status or "empty url",
                    )
                )
                checked_urls.add(link.url)
                continue

            if resolved.kind == LinkKind.LOCAL:
                checked_urls.add(link.url)
                result = check_local(resolved)
                if result.broken:
                    broken.append(
                        BrokenLink(
                            file=rel_file,
                            line=link.line,
                            text=link.text,
                            url=link.url,
                            status=result.status or "missing file",
                        )
                    )
                elif result.warning:
                    warnings.append(
                        HeadingWarning(
                            file=rel_file,
                            line=link.line,
                            url=link.url,
                            missing_heading=result.warning,
                        )
                    )
                continue

            if resolved.kind == LinkKind.HTTP:
                http_url = resolved.url
                checked_urls.add(http_url)
                http_result = http_checker.check(http_url)
                if not http_result.ok:
                    broken.append(
                        BrokenLink(
                            file=rel_file,
                            line=link.line,
                            text=link.text,
                            url=link.url,
                            status=http_result.status,
                        )
                    )

    print_report(
        file_count=len(md_files),
        unique_links=len(checked_urls),
        broken=broken,
        warnings=warnings,
    )

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
