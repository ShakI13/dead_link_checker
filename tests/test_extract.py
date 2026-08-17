"""Tests for src.extract."""

import unittest

from src.extract import extract_links
from src.resolve import LinkKind, classify_and_resolve
from pathlib import Path


class ExtractTests(unittest.TestCase):
    def test_inline_and_image_links(self) -> None:
        text = "[link text](page.md)\n![alt text](img.png)\n"
        links = extract_links(text)
        urls = [lk.url for lk in links]
        self.assertIn("page.md", urls)
        self.assertIn("img.png", urls)

    def test_autolink(self) -> None:
        text = "See <https://example.com/path> for info.\n"
        links = extract_links(text)
        self.assertEqual(links[0].url, "https://example.com/path")

    def test_reference_links(self) -> None:
        text = "[visible][ref-id]\n\n[ref-id]: target.md\n"
        links = extract_links(text)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, "target.md")
        self.assertEqual(links[0].text, "visible")

    def test_bare_url(self) -> None:
        text = "Visit https://example.com/page.\n"
        links = extract_links(text)
        self.assertEqual(links[0].url, "https://example.com/page")

    def test_html_href(self) -> None:
        text = '<a href="other.html">link</a>\n'
        links = extract_links(text)
        self.assertEqual(links[0].url, "other.html")

    def test_skips_fenced_code(self) -> None:
        text = "```\n[fake](broken.md)\nhttps://bad.example\n```\n"
        links = extract_links(text)
        self.assertEqual(links, [])

    def test_skips_inline_code(self) -> None:
        text = "Use `[text](nope.md)` in docs.\n"
        links = extract_links(text)
        self.assertEqual(links, [])

    def test_mailto_skipped_at_classify(self) -> None:
        text = "[email](mailto:user@example.com)\n"
        links = extract_links(text)
        self.assertEqual(len(links), 1)
        resolved = classify_and_resolve(links[0].url, Path("/tmp/doc.md"))
        self.assertEqual(resolved.kind, LinkKind.SKIP)

    def test_inline_http_url_not_recaptured_as_bare(self) -> None:
        text = "[https://example.com](https://example.com)\n"
        links = extract_links(text)
        self.assertEqual([lk.url for lk in links], ["https://example.com"])

    def test_badge_link_with_nested_image(self) -> None:
        text = (
            "[![Docs](https://img.shields.io/badge/Documentation-1.0.0-blue.svg)]"
            "(https://github.com/example/project/wiki)\n"
        )
        links = extract_links(text)
        urls = [lk.url for lk in links]
        self.assertIn(
            "https://img.shields.io/badge/Documentation-1.0.0-blue.svg",
            urls,
        )
        self.assertIn("https://github.com/example/project/wiki", urls)
        outer = next(
            lk for lk in links if lk.url == "https://github.com/example/project/wiki"
        )
        self.assertEqual(outer.text, "Docs")


if __name__ == "__main__":
    unittest.main()
