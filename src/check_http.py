"""Sequential HTTP link checking with caching."""

import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

# urllib's default User-Agent is "Python-urllib/x.y", which many CDNs/WAFs
# (Cloudflare, shields.io, etc.) reject with 403. A browser-like UA is accepted.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class HttpCheckResult:
    ok: bool
    status: str


class HttpChecker:
    """Check HTTP(S) URLs sequentially with a result cache."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self._cache: dict[str, HttpCheckResult] = {}

    def check(self, url: str) -> HttpCheckResult:
        if url in self._cache:
            return self._cache[url]
        result = self._fetch(url)
        self._cache[url] = result
        return result

    def _fetch(self, url: str) -> HttpCheckResult:
        # Try HEAD first; some sites (Figma, GitHub blob pages) lie on HEAD
        # (404/429) but respond OK to GET, which is what browsers use.
        result = self._request(url, method="HEAD")
        if result.ok:
            return result
        return self._request(url, method="GET")

    def _request(self, url: str, method: str) -> HttpCheckResult:
        req = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                code = resp.status
                if 200 <= code <= 299:
                    return HttpCheckResult(ok=True, status=str(code))
                return HttpCheckResult(ok=False, status=str(code))
        except urllib.error.HTTPError as exc:
            code = exc.code
            if 200 <= code <= 299:
                return HttpCheckResult(ok=True, status=str(code))
            return HttpCheckResult(ok=False, status=str(code))
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout):
                return HttpCheckResult(ok=False, status="timeout")
            if isinstance(reason, TimeoutError):
                return HttpCheckResult(ok=False, status="timeout")
            if isinstance(reason, ssl.SSLError):
                return HttpCheckResult(ok=False, status="ssl error")
            if isinstance(reason, ConnectionError):
                return HttpCheckResult(ok=False, status="connection error")
            msg = str(reason).lower()
            if "redirect" in msg or "location" in msg:
                return HttpCheckResult(ok=False, status="redirect error")
            if "timed out" in msg or "timeout" in msg:
                return HttpCheckResult(ok=False, status="timeout")
            if "ssl" in msg or "certificate" in msg:
                return HttpCheckResult(ok=False, status="ssl error")
            if "name or service not known" in msg or "nodename" in msg:
                return HttpCheckResult(ok=False, status="connection error")
            return HttpCheckResult(ok=False, status="connection error")
        except socket.timeout:
            return HttpCheckResult(ok=False, status="timeout")
        except TimeoutError:
            return HttpCheckResult(ok=False, status="timeout")
        except ssl.SSLError:
            return HttpCheckResult(ok=False, status="ssl error")
        except ConnectionError:
            return HttpCheckResult(ok=False, status="connection error")
