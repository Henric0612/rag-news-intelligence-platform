"""GitHub REST client used by the release workflow (standard library only)."""

import json
import urllib.parse

from .transport import request_following_redirects, urllib_transport

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
PAGE_SIZE = 100
MAX_PAGES = 50


class GitHubError(RuntimeError):
    """A GitHub API request returned an unexpected result."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class GitHubClient:
    def __init__(self, token, repository, transport=urllib_transport, api_url=API_URL):
        if not token:
            raise GitHubError("GITHUB_TOKEN is required")
        self.token = token
        self.repository = repository
        self.transport = transport
        self.api_url = api_url.rstrip("/")

    def _headers(self, accept="application/vnd.github+json", extra=None):
        headers = {
            "Accept": accept,
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "rag-delivery",
        }
        headers.update(extra or {})
        return headers

    def url(self, path):
        if path.startswith("https://"):
            return path
        return f"{self.api_url}/repos/{self.repository}/{path.lstrip('/')}"

    def request(self, method, path, payload=None, accept="application/vnd.github+json",
                body=None, content_type=None, follow=False):
        extra = {}
        if payload is not None:
            body = json.dumps(payload).encode()
            content_type = "application/json"
        if content_type:
            extra["Content-Type"] = content_type
        headers = self._headers(accept, extra)
        if follow:
            return request_following_redirects(self.transport, method, self.url(path), headers, body)
        return self.transport(method, self.url(path), headers, body)

    def json(self, method, path, payload=None, expect=(200,)):
        response = self.request(method, path, payload)
        if response.status not in expect:
            raise GitHubError(
                f"{method} {path}: HTTP {response.status}: {response.body[:300]!r}",
                response.status,
            )
        return json.loads(response.body) if response.body else None

    def get_optional(self, path):
        """GET returning (status, json-or-None); only 200 and 404 are expected."""
        response = self.request("GET", path)
        if response.status == 404:
            return 404, None
        if response.status != 200:
            raise GitHubError(
                f"GET {path}: HTTP {response.status}: {response.body[:300]!r}",
                response.status,
            )
        return 200, json.loads(response.body)

    def paginate(self, path, key=None):
        """Collect every page of a list endpoint, failing closed on truncation."""
        separator = "&" if "?" in path else "?"
        items = []
        total = None
        for page in range(1, MAX_PAGES + 1):
            data = self.json("GET", f"{path}{separator}per_page={PAGE_SIZE}&page={page}")
            chunk = data[key] if key else data
            if key and "total_count" in data:
                total = data["total_count"]
            items.extend(chunk)
            if len(chunk) < PAGE_SIZE:
                break
        else:
            raise GitHubError(f"GET {path}: more than {MAX_PAGES} pages")
        if total is not None and total != len(items):
            raise GitHubError(f"GET {path}: total_count {total} != {len(items)} items")
        return items

    def upload_asset(self, upload_url, name, data, content_type):
        base = upload_url.split("{", 1)[0]
        url = f"{base}?{urllib.parse.urlencode({'name': name})}"
        response = self.transport(
            "POST", url, self._headers(extra={"Content-Type": content_type}), data
        )
        if response.status != 201:
            raise GitHubError(
                f"upload {name}: HTTP {response.status}: {response.body[:300]!r}",
                response.status,
            )
        return json.loads(response.body)

    def download_asset(self, asset_id):
        response = self.request(
            "GET", f"releases/assets/{asset_id}", accept="application/octet-stream", follow=True
        )
        if response.status != 200:
            raise GitHubError(f"download asset {asset_id}: HTTP {response.status}", response.status)
        return response.body
