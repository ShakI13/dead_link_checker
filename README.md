# Markdown Link Checker

Recursively scan a project folder for Markdown files, extract links, check local targets and HTTP(S) URLs, and print a **rich** console report of broken links and heading warnings.

## Requirements

- Python 3.13.5
- Third-party dependency: `rich` only

## Setup

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python check_links.py PATH [--timeout SECONDS]
```

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `PATH` | yes | — | Directory to scan (must exist and be a directory) |
| `--timeout` | no | `10` | HTTP timeout in seconds (must be > 0) |

Example:

```bash
python check_links.py ./some_project --timeout 5
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No broken links (heading warnings are allowed) |
| `1` | At least one broken link |
| `2` | Usage error, invalid PATH, or invalid `--timeout` |

## Tests

```bash
source venv/bin/activate
python -m unittest discover -s tests -v
```

Tests use `unittest` only and do not hit the real network.

## What it checks

- Inline links, images, autolinks, reference-style links, bare URLs, and HTML `<a href>` tags in `.md` files
- Local files and directories (relative to the source `.md` file directory)
- HTTP(S) URLs (sequential, with HEAD-then-GET fallback when HEAD is not 2xx)
- Heading fragments in target Markdown files (missing headings are warnings, not broken links)

Skipped: `mailto:`, `tel:`, `data:`, and other non-HTTP schemes; links inside fenced or inline code blocks.

See [docs/SPEC.md](docs/SPEC.md) for the full specification.
