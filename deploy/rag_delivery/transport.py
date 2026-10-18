"""Minimal HTTP transport with explicit redirect handling.

Redirects are never followed automatically: GitHub release assets and GHCR
blobs redirect to signed storage URLs, and credentials must not be forwarded
to a different host.
"""

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

REDIRECT_STATUSES = (301, 302, 303, 307, 308)
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 60


class TransportError(RuntimeError):
    """The request could not be completed (network failure or redirect loop)."""


@dataclass
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""

    def header(self, name):
        return self.headers.get(name.lower())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_transport(method, url, headers=None, body=None):
    """Perform one HTTP request; non-2xx statuses are returned, not raised."""
    request = urllib.request.Request(url, data=body, method=method)
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    try:
        with _OPENER.open(request, timeout=TIMEOUT_SECONDS) as reply:
            return Response(
                reply.status,
                {k.lower(): v for k, v in reply.headers.items()},
                reply.read(),
            )
    except urllib.error.HTTPError as error:
        return Response(
            error.code,
            {k.lower(): v for k, v in (error.headers or {}).items()},
            error.read() or b"",
        )
    except (urllib.error.URLError, OSError) as error:
        raise TransportError(f"{method} {url}: {error}") from error


def request_following_redirects(transport, method, url, headers=None, body=None):
    """Follow redirects manually, dropping Authorization on a host change."""
    headers = dict(headers or {})
    origin = urllib.parse.urlsplit(url).netloc
    for _ in range(MAX_REDIRECTS + 1):
        response = transport(method, url, headers, body)
        if response.status not in REDIRECT_STATUSES:
            return response
        location = response.header("location")
        if not location:
            return response
        url = urllib.parse.urljoin(url, location)
        if urllib.parse.urlsplit(url).netloc != origin:
            headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}
        if response.status == 303:
            method, body = "GET", None
    raise TransportError(f"too many redirects for {url}")
