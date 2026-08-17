"""Rich console report for broken links and heading warnings."""

from dataclasses import dataclass

from rich.console import Console
from rich.table import Table


@dataclass
class BrokenLink:
    file: str
    line: int
    text: str
    url: str
    status: str


@dataclass
class HeadingWarning:
    file: str
    line: int
    url: str
    missing_heading: str


def print_report(
    file_count: int,
    unique_links: int,
    broken: list[BrokenLink],
    warnings: list[HeadingWarning],
) -> None:
    """Print summary and tables to stdout."""
    console = Console()
    broken_count = len(broken)
    warning_count = len(warnings)

    console.print(
        f"Scanned {file_count} file(s), checked {unique_links} unique link(s): "
        f"{broken_count} broken, {warning_count} warning(s)."
    )

    if broken:
        table = Table(title="Broken Links", show_header=True, header_style="bold red")
        table.add_column("File")
        table.add_column("Line", justify="right")
        table.add_column("Text")
        table.add_column("URL")
        table.add_column("Status")
        for item in sorted(broken, key=lambda x: (x.file, x.line)):
            table.add_row(
                item.file,
                str(item.line),
                item.text,
                item.url,
                item.status,
            )
        console.print(table)

    if warnings:
        table = Table(
            title="Heading Warnings", show_header=True, header_style="bold yellow"
        )
        table.add_column("File")
        table.add_column("Line", justify="right")
        table.add_column("URL")
        table.add_column("Missing heading")
        for item in sorted(warnings, key=lambda x: (x.file, x.line)):
            table.add_row(
                item.file,
                str(item.line),
                item.url,
                item.missing_heading,
            )
        console.print(table)

    if not broken and not warnings:
        console.print("[green]All links are OK.[/green]")
