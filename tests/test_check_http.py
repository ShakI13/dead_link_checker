"""Tests for src.check_http."""

import io
import unittest
from unittest import mock

from src.check_http import USER_AGENT, HttpChecker


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class CheckHttpTests(unittest.TestCase):
    def test_200_is_ok(self) -> None:
        checker = HttpChecker(timeout=5)
        with mock.patch(
            "urllib.request.urlopen",
            return_value=FakeResponse(200),
        ):
            result = checker.check("https://example.com/ok")
        self.assertTrue(result.ok)

    def test_404_is_broken(self) -> None:
        import urllib.error

        checker = HttpChecker(timeout=5)
        err = urllib.error.HTTPError(
            "https://example.com/missing",
            404,
            "Not Found",
            {},
            io.BytesIO(b""),
        )
        with mock.patch("urllib.request.urlopen", side_effect=err):
            result = checker.check("https://example.com/missing")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "404")

    def test_timeout_is_broken(self) -> None:
        import socket
        import urllib.error

        checker = HttpChecker(timeout=1)
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError(socket.timeout("timed out")),
        ):
            result = checker.check("https://example.com/slow")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "timeout")

    def test_head_405_then_get_200(self) -> None:
        import urllib.error

        checker = HttpChecker(timeout=5)

        def side_effect(req: object, timeout: float) -> FakeResponse:
            method = getattr(req, "method", "GET")
            if method == "HEAD":
                raise urllib.error.HTTPError(
                    "https://example.com/",
                    405,
                    "Method Not Allowed",
                    {},
                    io.BytesIO(b""),
                )
            return FakeResponse(200)

        with mock.patch("urllib.request.urlopen", side_effect=side_effect):
            result = checker.check("https://example.com/")
        self.assertTrue(result.ok)

    def test_head_404_then_get_200(self) -> None:
        import urllib.error

        checker = HttpChecker(timeout=5)

        def side_effect(req: object, timeout: float) -> FakeResponse:
            method = getattr(req, "method", "GET")
            if method == "HEAD":
                raise urllib.error.HTTPError(
                    "https://www.figma.com/design/x",
                    404,
                    "Not Found",
                    {},
                    io.BytesIO(b""),
                )
            return FakeResponse(200)

        with mock.patch("urllib.request.urlopen", side_effect=side_effect):
            result = checker.check("https://www.figma.com/design/x")
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "200")

    def test_head_429_then_get_200(self) -> None:
        import urllib.error

        checker = HttpChecker(timeout=5)

        def side_effect(req: object, timeout: float) -> FakeResponse:
            method = getattr(req, "method", "GET")
            if method == "HEAD":
                raise urllib.error.HTTPError(
                    "https://github.com/org/repo/blob/main/file",
                    429,
                    "Too Many Requests",
                    {"Server": "Varnish"},
                    io.BytesIO(b""),
                )
            return FakeResponse(200)

        with mock.patch("urllib.request.urlopen", side_effect=side_effect):
            result = checker.check("https://github.com/org/repo/blob/main/file")
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "200")

    def test_403_without_user_agent_ok_with_browser_user_agent(self) -> None:
        """Sites that block Python-urllib return 403 unless a browser UA is sent."""
        import urllib.error
        import urllib.request

        url = "https://feature-sliced.design/"

        def waf_like_urlopen(req: urllib.request.Request, timeout: float) -> FakeResponse:
            ua = req.get_header("User-agent") or ""
            if not ua or ua.startswith("Python-urllib"):
                raise urllib.error.HTTPError(
                    url,
                    403,
                    "Forbidden",
                    {},
                    io.BytesIO(b""),
                )
            return FakeResponse(200)

        with mock.patch("urllib.request.urlopen", side_effect=waf_like_urlopen):
            bare = urllib.request.Request(url, method="GET")
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(bare, timeout=5)
            self.assertEqual(raised.exception.code, 403)

            result = HttpChecker(timeout=5).check(url)
            self.assertTrue(result.ok)
            self.assertEqual(result.status, "200")

        captured: list[str | None] = []

        def capture_ua(req: urllib.request.Request, timeout: float) -> FakeResponse:
            captured.append(req.get_header("User-agent"))
            return FakeResponse(200)

        with mock.patch("urllib.request.urlopen", side_effect=capture_ua):
            HttpChecker(timeout=5).check("https://example.com/ua")
        self.assertEqual(captured, [USER_AGENT])


if __name__ == "__main__":
    unittest.main()
