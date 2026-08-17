# Markdown Link Checker — Implementation Spec

Build a CLI that recursively scans a project folder for Markdown files, extracts links, checks local targets and HTTP(S) URLs, and prints a **rich** console report of **broken links** plus **heading warnings**. This is **not** a Python dead-code checker.

Do not use `.env`. There are no secrets. Timeout is a CLI argument.

---

## Confirmed rules

| Topic | Decision |
| --- | --- |
| Scope | Links inside `.md` files only |
| Recursion | Yes, whole tree under the given folder |
| Skip directories | `.git`, `venv`, `node_modules`, `__pycache__` (any nesting) |
| Link forms | Inline `[text](url)`, images `![alt](url)`, autolinks `<https://...>`, reference-style `[text][ref]` / `[ref]: url` / collapsed `[text][]` / shortcut `[text]` when a definition exists, bare `http(s)://` URLs, HTML `<a href="...">` / `<a href='...'>` |
| Skip schemes | `mailto:`, `tel:`, `data:` — do not check, do not report |
| Other schemes | Skip (`javascript:`, `ftp:`, etc.) |
| Anchors | Check file **and** heading. Missing heading = **warning**, not broken |
| Relative URLs | Resolve against the **directory of the current `.md` file**, not cwd, not scan root |
| Directory links | OK if the directory exists |
| Absolute paths (`/foo`) | Filesystem root (POSIX path), not project root |
| `file://` | Decode URL, check the filesystem path |
| HTTP | Sequential (no thread pool). Timeout from `--timeout`. Send a browser-like User-Agent (Python-urllib is often 403). Follow redirects. SSL verify on |
| Broken HTTP | Final 4xx/5xx (including 429), redirect failure/loop, timeout, DNS, connection, SSL errors |
| HEAD/GET | Try `HEAD` first. If HEAD is not 2xx, retry once with `GET`. Use the GET response as the result |
| Report | Only broken links + heading warnings. Do not list OK links |
| Colors/table | `rich` is allowed and required for the report |
| Entry | `check_links.py` in project root; imports implementation from `src/` |
| Tests | `unittest` only (not pytest) |
| Python | 3.13.5, virtualenv at `./venv` |
| Third-party | `rich` only (stdlib for HTTP, paths, parsing) |

---

## Project layout

```
check_links.py          # CLI: argparse, sys.exit, imports src
src/
  __init__.py
  discover.py           # find .md files; skip ignored dirs
  extract.py            # parse links from one markdown document
  headings.py           # heading texts + GitHub-like slugs
  resolve.py            # classify + resolve to local path / http url / skip
  check_local.py        # exists file/dir; heading warning
  check_http.py         # sequential HEAD/GET with timeout
  report.py             # rich tables
tests/
  test_discover.py
  test_extract.py
  test_headings.py
  test_resolve.py
  test_check_local.py
  test_check_http.py
  fixtures/             # small .md trees for tests
docs/
  SPEC.md               # this file
requirements.txt        # rich
README.md               # how to install and run
```

Keep modules small. Do not add extra flags, config files, or libraries.

---

## CLI

```
python check_links.py PATH [--timeout SECONDS]
```

| Arg | Required | Default | Meaning |
| --- | --- | --- | --- |
| `PATH` | yes | — | Directory to scan. Must exist and be a directory |
| `--timeout` | no | `10` | HTTP timeout in seconds (float allowed). Must be `> 0` |

Examples:

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python check_links.py ./some_project --timeout 5
```

### Exit codes

| Code | When |
| --- | --- |
| `0` | No broken links (heading warnings are allowed) |
| `1` | At least one broken link |
| `2` | Usage / bad PATH / `--timeout` invalid |

Print usage errors to stderr.

---

## Discover Markdown files

- Walk `PATH` recursively.
- Collect files whose name ends with `.md` (case-insensitive: `.md`, `.MD`).
- Do not descend into a directory named `.git`, `venv`, `node_modules`, or `__pycache__`.
- Skip symlinks to files outside the scan if following them is awkward; following directory symlinks is not required. Regular files are enough.
- Process files in sorted path order for stable output.

---

## Extract links

Parse each file as text (UTF-8). If a file is not valid UTF-8, skip it and print a short stderr warning; do not crash.

### Ignore these regions (do not extract links from them)

1. Fenced code blocks: ` ``` ` or ` ~~~ ` (closing fence of the same kind).
2. Inline code: text between unescaped backticks.

This is mandatory. Example URLs in docs must not be checked.

### Extract these (outside ignored regions)

1. **Inline / image:** `[text](destination)` and `![alt](destination)`  
   - Destination may be `<url>` or raw.  
   - Optional title: `[t](url "title")` / `[t](url 'title')` — URL is the first token.  
   - Record link text, URL, and 1-based line number of the `[`.

2. **Autolink:** `<http://...>` or `<https://...>`.

3. **Reference definitions:** `[id]: url` or `[id]: <url>` (optional title). Map normalized id → url. Ids are case-insensitive, trimmed.

4. **Reference usage:** `[text][id]`, collapsed `[text][]` (id = text), shortcut `[text]` **only if** a definition for that id exists. If no definition, ignore (do not treat as broken).

5. **Bare URLs:** `http://` or `https://` not already captured. Trim trailing `.,;:!?)`.

6. **HTML:** `<a href="url">` and `<a href='url'>` (case-insensitive tag/attr).

Deduplicate **extractions** that are the same `(file, line, url)` so a URL matching both autolink and bare-url rules is reported once. The same URL on different lines is multiple findings.

---

## Classify and resolve

For each extracted URL string, strip surrounding whitespace.

| URL | Action |
| --- | --- |
| empty | Broken: empty URL |
| `mailto:`, `tel:`, `data:` | Skip |
| other non-checked scheme (`javascript:`, `ftp:`, …) | Skip |
| `http://` or `https://` | HTTP check (use URL as written) |
| `//host/path` | HTTP check as `https://host/path` |
| `file://` | Local: `urllib.parse.urlparse` + `unquote` path; on POSIX the path is `parsed.path` |
| `#fragment` only | Local: current `.md` file + heading check |
| everything else | Local path (relative or absolute) |

### Local path resolution

1. Split off fragment (`#...`) and query (`?...`) **before** filesystem checks. Keep the fragment for heading check.
2. URL-decode `%20` etc. (`urllib.parse.unquote`).
3. If the path is absolute (`posixpath.isabs` / starts with `/`), use it as a filesystem path from root.
4. If relative, join with `Path(markdown_file).parent` and `resolve()` (normalize `..`).
5. Existence:
   - If the path exists as a **file** or **directory** → file part OK.
   - Else → **broken** (`status`: missing file, no HTTP code).

Do not require a `.md` suffix. `README` and `docs/` are fine if they exist.

### Heading check (warning only)

If a fragment is present and the file part is OK:

- Load the **target file** (current file for `#only`, or the resolved path).
- If the target is a **directory**, skip heading check (no warning).
- If the target is not Markdown (extension not `.md`), skip heading check.
- If the target is Markdown: compute heading slugs (see below). If the fragment (URL-decoded, case-sensitive against the slug) is **not** in the slug set → **warning**.

Missing heading never makes the link broken and never sets exit code 1 by itself.

---

## Heading slugs (GitHub-like)

From the **target markdown file**, collect headings:

- ATX: line matching `^(#{1,6})\s+(.+?)\s*#*\s*$`
- Setext: a text line followed by `===` (h1) or `---` (h2)

Ignore headings inside fenced code blocks.

**Slug algorithm** (apply in order):

1. Strip markdown emphasis from heading text: remove wrapping `` ` ``, `*`, `_`, and replace `[label](url)` / `[label][id]` with `label`.
2. Lowercase (Unicode).
3. Remove characters that are not Unicode letters, numbers, spaces, hyphens, or underscores.
4. Trim, then replace runs of spaces and/or hyphens with a single hyphen.
5. Strip leading/trailing hyphens.

**Duplicates:** first occurrence is `slug`; next are `slug-1`, `slug-2`, …

**Fragment match:** compare to the slug string (after `unquote` of the fragment). Do not lowercase the fragment again beyond the slug rules — slugs are already lowercase, so `#Hello-World` vs `hello-world`: unquote then lowercase the fragment before compare, so typical Markdown anchors work.

Examples:

| Heading | Slug |
| --- | --- |
| `Hello World` | `hello-world` |
| `Foo bar` (second such heading) | `foo-bar-1` |
| `A_B` | `a_b` |

---

## HTTP check

- Sequential, one request at a time.
- Cache by exact URL string: the same URL in many files is requested **once**; reuse status for all findings.
- Timeout: `--timeout` for connect and read (`urllib.request.urlopen(..., timeout=timeout)`).
- Follow redirects (urllib default). Redirect loop / missing Location → broken, status `redirect error`.
- SSL errors, `socket.timeout`, `TimeoutError`, `URLError` (DNS, connection) → broken. Put the reason in the status column (e.g. `timeout`, `connection error`, `ssl error`). No traceback in the report.
- Success: **final** status `200–299` is OK (redirects that land on 2xx are OK).
- Broken HTTP statuses: final `300–399` (redirect not completed), all `400–599` (including 429), plus timeout / DNS / connection / SSL as above.
- Do not retry except the HEAD→GET fallback described above.
- Send a browser-like `User-Agent` header. urllib's default `Python-urllib/x.y` is commonly blocked with 403 (Cloudflare, shields.io, docs sites).

Implementation: stdlib `urllib.request` only.

---

## Report (`rich`)

Print to stdout.

1. A one-line summary: scanned file count, unique links checked, broken count, warning count.
2. If there are broken links, a **red** table, columns:

   | File | Line | Text | URL | Status |
   | --- | --- | --- | --- | --- |

   `Status` is HTTP code (`404`, `500`, `429`) or a short reason (`missing file`, `timeout`, `connection error`, `empty url`, `redirect error`, `ssl error`).

3. If there are heading warnings, a **yellow** table, columns:

   | File | Line | URL | Missing heading |

4. If nothing is broken and no warnings: print a green line that all links are OK.

Sort tables by file path, then line number.

Do not print OK links.

---

## Tests (`unittest`)

Use `./venv` if present. Do not use pytest.

```bash
source venv/bin/activate
python -m unittest discover -s tests -v
```

Use `tempfile.TemporaryDirectory` for files and `unittest.mock` to patch HTTP. Tests must not hit the real network.

Minimum cases:

| Area | Cases |
| --- | --- |
| discover | finds nested `.md`; does not enter `venv` / `.git` / `node_modules` / `__pycache__` |
| extract | inline, image, autolink, reference, bare URL, `<a href>`; skips fenced and inline code; skips `mailto:` at classify time |
| resolve | `../x.md` relative to the **source file dir**; `/tmp/...` as filesystem absolute; `file:///...`; `#anchor` |
| local | missing file → broken; existing dir → OK; existing file → OK |
| headings | missing slug → warning not broken; duplicate headings get `-1` suffix |
| http | mock 200 OK; mock 404 broken; timeout → broken; HEAD 405 then GET 200 → OK; HEAD 404 then GET 200 → OK; HEAD 429 then GET 200 → OK; mock 403 without User-Agent and 200 with browser User-Agent |

---

## Acceptance criteria

- [ ] `venv` created with Python 3.13.5; `rich` in `requirements.txt`
- [ ] `python check_links.py PATH [--timeout N]` works from repo root
- [ ] Relative links resolve from the `.md` file directory
- [ ] HTTP uses timeout; 404/500/429/timeout/connection errors show as broken with status
- [ ] Missing headings are warnings (exit 0 if that is the only issue)
- [ ] `mailto:` / `tel:` / `data:` ignored
- [ ] Links in fenced/inline code ignored
- [ ] Report uses `rich` tables; OK links omitted
- [ ] Exit `1` when any link is broken
- [ ] `python -m unittest discover -s tests -v` passes without network

---

## Out of scope

- Dead Python code / unused imports
- Checking non-`.md` files
- Concurrent HTTP
- `.env`, config files, extra CLI flags
- Writing a cache to disk
- pytest
