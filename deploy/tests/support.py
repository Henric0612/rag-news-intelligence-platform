"""Controlled fixtures for the delivery tests: no network, no Docker, no GitHub."""

import copy
import hashlib
import json
import re
import urllib.parse

from deploy.rag_delivery.contract import (
    CHECK_APP_ID,
    IMAGE_REPOSITORIES,
    REPOSITORY,
    REQUIRED_CHECKS,
)
from deploy.rag_delivery.transport import Response

SHA = "6e5af4a85e3d7ace582611415f1f9c2fc16cea8e"
TAG_OBJECT_SHA = "0123456789abcdef0123456789abcdef01234567"
VERSION = "v0.1.0"
APP_VERSION = "0.1.0"
SHA_TAG = "sha-6e5af4a"
RUN_ID = 39165857610
SUITE_ID = 106132825242
RELEASE_RUN_ID = 40000000001
API = f"https://api.github.com/repos/{REPOSITORY}"
MEDIA_OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
MEDIA_OCI_INDEX = "application/vnd.oci.image.index.v1+json"
MEDIA_DOCKER_MANIFEST = "application/vnd.docker.distribution.manifest.v2+json"


def digest_of(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


# --- GitHub API payloads (shapes follow real responses for this repository) ---

def repo_doc(name=REPOSITORY):
    return {"full_name": name}


def ci_run(**overrides):
    run = {
        "id": RUN_ID, "name": "Daily CI", "path": ".github/workflows/ci.yml",
        "event": "push", "head_branch": "main", "head_sha": SHA, "run_attempt": 1,
        "status": "completed", "conclusion": "success", "check_suite_id": SUITE_ID,
        "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}",
        "created_at": "2026-10-18T21:00:17Z", "updated_at": "2026-10-18T21:05:00Z",
        "repository": repo_doc(), "head_repository": repo_doc(),
    }
    run.update(overrides)
    return run


CHECK_IDS = {name: 117788542000 + i for i, name in enumerate(REQUIRED_CHECKS)}


def job(name, check_id=None, **overrides):
    check_id = check_id or CHECK_IDS[name]
    data = {
        "id": check_id, "name": name, "run_id": RUN_ID, "run_attempt": 1, "head_sha": SHA,
        "status": "completed", "conclusion": "success",
        "check_run_url": f"https://api.github.com/repos/{REPOSITORY}/check-runs/{check_id}",
        "started_at": "2026-10-18T21:00:20Z", "completed_at": "2026-10-18T21:03:00Z",
    }
    data.update(overrides)
    return data


def check_run(name, check_id=None, **overrides):
    data = {
        "id": check_id or CHECK_IDS[name], "name": name, "head_sha": SHA,
        "status": "completed", "conclusion": "success",
        "app": {"slug": "github-actions", "id": CHECK_APP_ID},
        "check_suite": {"id": SUITE_ID},
        "details_url": f"https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}/job/1",
        "started_at": "2026-10-18T21:00:20Z", "completed_at": "2026-10-18T21:03:00Z",
    }
    data.update(overrides)
    return data


def all_jobs(**overrides):
    return [job(name, **overrides) for name in REQUIRED_CHECKS]


def all_check_runs(**overrides):
    return [check_run(name, **overrides) for name in REQUIRED_CHECKS]


def tag_ref_doc(version=VERSION, object_type="tag", sha=TAG_OBJECT_SHA):
    return {"ref": f"refs/tags/{version}", "object": {"type": object_type, "sha": sha}}


def tag_object_doc(version=VERSION, commit=SHA, object_type="commit", sha=TAG_OBJECT_SHA):
    return {"sha": sha, "tag": version, "object": {"type": object_type, "sha": commit}}


def push_env(**overrides):
    env = {
        "GITHUB_EVENT_NAME": "push", "GITHUB_REF": f"refs/tags/{VERSION}",
        "GITHUB_REF_NAME": VERSION, "GITHUB_SHA": SHA, "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_RUN_ID": str(RELEASE_RUN_ID), "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/.github/workflows/release.yml@refs/tags/{VERSION}",
    }
    env.update(overrides)
    return env


def dispatch_env(**overrides):
    env = {
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_REF_NAME": "main", "GITHUB_SHA": SHA, "GITHUB_REPOSITORY": REPOSITORY,
        "INPUT_SHA": SHA, "INPUT_VERSION": VERSION,
        "GITHUB_RUN_ID": str(RELEASE_RUN_ID), "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/.github/workflows/release.yml@refs/heads/main",
    }
    env.update(overrides)
    return env


class FakeGitHubTransport:
    """Routes (METHOD, path) to JSON payloads; pagination parameters are ignored."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers or {}), body))
        parsed = urllib.parse.urlsplit(url)
        query = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k not in ("per_page", "page")]
        path = parsed.path
        prefix = f"/repos/{REPOSITORY}/"
        if parsed.netloc == "api.github.com" and path.startswith(prefix):
            path = path[len(prefix):]
        key = (method, path + ("?" + urllib.parse.urlencode(query) if query else ""))
        page = dict(urllib.parse.parse_qsl(parsed.query)).get("page", "1")
        if page != "1":
            return Response(200, {}, b"[]")
        handler = self.routes.get(key)
        if handler is None:
            return Response(404, {}, b'{"message":"Not Found"}')
        if callable(handler):
            return handler(method, url, headers, body)
        status, payload = handler
        return Response(status, {}, json.dumps(payload).encode() if payload is not None else b"")


def gate_routes(runs=None, jobs=None, check_runs=None, release_status=404, tag_ref=None, tag_obj=None):
    runs = [ci_run()] if runs is None else runs
    jobs = all_jobs() if jobs is None else jobs
    check_runs = all_check_runs() if check_runs is None else check_runs
    attempt = max([r["run_attempt"] for r in runs] or [1])
    return {
        ("GET", f"git/ref/tags/{VERSION}"): (200, tag_ref or tag_ref_doc()),
        ("GET", f"git/tags/{TAG_OBJECT_SHA}"): (200, tag_obj or tag_object_doc()),
        ("GET", f"actions/workflows/ci.yml/runs?head_sha={SHA}&event=push&branch=main"):
            (200, {"total_count": len(runs), "workflow_runs": runs}),
        ("GET", f"actions/runs/{RUN_ID}/attempts/{attempt}/jobs"):
            (200, {"total_count": len(jobs), "jobs": jobs}),
        ("GET", f"commits/{SHA}/check-runs?filter=all"):
            (200, {"total_count": len(check_runs), "check_runs": check_runs}),
        ("GET", f"releases/tags/{VERSION}"):
            (release_status, {"tag_name": VERSION, "draft": False} if release_status == 200 else {"message": "Not Found"}),
    }


# --- GHCR fake ---

class FakeImage:
    """One pushed image: a config blob, one image manifest, optionally an index."""

    def __init__(self, service, app_version=APP_VERSION, sha=SHA, use_index=False, layers=(1000, 5000)):
        labels = {
            "org.opencontainers.image.source": "https://github.com/Henric0612/rag-news-intelligence-platform",
            "org.opencontainers.image.version": app_version,
            "org.opencontainers.image.revision": sha,
            "org.opencontainers.image.title": f"rag-news-{service}",
        }
        self.config = json.dumps({"os": "linux", "architecture": "amd64", "config": {"Labels": labels}}).encode()
        manifest = {
            "schemaVersion": 2, "mediaType": MEDIA_OCI_MANIFEST,
            "config": {"mediaType": "application/vnd.oci.image.config.v1+json",
                       "digest": digest_of(self.config), "size": len(self.config)},
            "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                        "digest": "sha256:" + f"{i:064x}", "size": size} for i, size in enumerate(layers)],
        }
        self.manifest = json.dumps(manifest).encode()
        self.manifests = {digest_of(self.manifest): (MEDIA_OCI_MANIFEST, self.manifest)}
        self.top = digest_of(self.manifest)
        if use_index:
            attestation = json.dumps({"schemaVersion": 2, "mediaType": MEDIA_OCI_MANIFEST,
                                      "config": manifest["config"], "layers": []}).encode()
            index = json.dumps({"schemaVersion": 2, "mediaType": MEDIA_OCI_INDEX, "manifests": [
                {"mediaType": MEDIA_OCI_MANIFEST, "digest": digest_of(self.manifest),
                 "size": len(self.manifest), "platform": {"os": "linux", "architecture": "amd64"}},
                {"mediaType": MEDIA_OCI_MANIFEST, "digest": digest_of(attestation), "size": len(attestation),
                 "platform": {"os": "unknown", "architecture": "unknown"},
                 "annotations": {"vnd.docker.reference.type": "attestation-manifest"}},
            ]}).encode()
            self.manifests[digest_of(index)] = (MEDIA_OCI_INDEX, index)
            self.manifests[digest_of(attestation)] = (MEDIA_OCI_MANIFEST, attestation)
            self.top = digest_of(index)
        self.blobs = {digest_of(self.config): self.config}


class FakePackage:
    def __init__(self, public=False):
        self.public = public
        self.tags = {}
        self.manifests = {}
        self.blobs = {}

    def put(self, image, tags):
        self.manifests.update(image.manifests)
        self.blobs.update(image.blobs)
        for tag in tags:
            self.tags[tag] = image.top


class FakeRegistry:
    """GHCR behavior observed for anonymous requests, plus authenticated access.

    Anonymous tokens are granted only for existing public packages; missing
    and private packages are both DENIED (as observed on ghcr.io). With
    ``auth_ok`` credentials, tokens are granted for any package in the
    namespace and missing packages answer 404 NAME_UNKNOWN.
    """

    def __init__(self, packages=None, auth_ok=True, auth_denied_repos=(), fail_urls=()):
        self.packages = dict(packages or {})
        self.auth_ok = auth_ok
        self.auth_denied_repos = set(auth_denied_repos)
        self.fail_urls = tuple(fail_urls)
        self.calls = []
        self._tokens = {}

    @staticmethod
    def name(service):
        return IMAGE_REPOSITORIES[service].split("/", 1)[1]

    def __call__(self, method, url, headers, body):
        from deploy.rag_delivery.transport import TransportError
        headers = dict(headers or {})
        self.calls.append((method, url, headers))
        if any(url.startswith(prefix) for prefix in self.fail_urls):
            raise TransportError(f"simulated network failure for {url}")
        parsed = urllib.parse.urlsplit(url)
        if parsed.netloc == "storage.example":
            if "Authorization" in headers:
                return Response(400, {}, b"credentials forwarded to storage host")
            repo, digest = parsed.path.lstrip("/").rsplit("/", 1)
            return Response(200, {}, self.packages[repo].blobs[digest])
        if parsed.path == "/token":
            scope = dict(urllib.parse.parse_qsl(parsed.query))["scope"]
            repo = scope.split(":")[1]
            package = self.packages.get(repo)
            if "Authorization" in headers:
                granted = self.auth_ok and repo not in self.auth_denied_repos
            else:
                granted = package is not None and package.public
            if not granted:
                return Response(403, {}, b'{"errors":[{"code":"DENIED","message":"requested access to the resource is denied"}]}')
            token = f"tok-{len(self._tokens)}"
            self._tokens[token] = repo
            return Response(200, {}, json.dumps({"token": token}).encode())
        match = re.fullmatch(r"/v2/(.+)/(manifests|blobs)/(.+)", parsed.path)
        token = headers.get("Authorization", "").removeprefix("Bearer ")
        if not match or self._tokens.get(token) != match.group(1):
            return Response(401, {}, b'{"errors":[{"code":"UNAUTHORIZED"}]}')
        repo, kind, reference = match.groups()
        package = self.packages.get(repo)
        if package is None:
            return Response(404, {}, b'{"errors":[{"code":"NAME_UNKNOWN","message":"repository name not known"}]}')
        if kind == "blobs":
            if reference not in package.blobs:
                return Response(404, {}, b'{"errors":[{"code":"BLOB_UNKNOWN"}]}')
            return Response(307, {"location": f"https://storage.example/{repo}/{reference}"}, b"")
        digest = package.tags.get(reference, reference if reference.startswith("sha256:") else None)
        if digest not in package.manifests:
            return Response(404, {}, b'{"errors":[{"code":"MANIFEST_UNKNOWN","message":"manifest unknown"}]}')
        media_type, data = package.manifests[digest]
        return Response(200, {"content-type": media_type, "docker-content-digest": digest}, data)


def published_registry(public=True, use_index=False, frontend_version_digest=None):
    """A registry where both images carry both release tags."""
    packages = {}
    images = {}
    for service in ("backend", "frontend"):
        image = FakeImage(service, use_index=use_index, layers=(1000, 5000) if service == "backend" else (300, 700))
        package = FakePackage(public=public)
        package.put(image, [SHA_TAG, VERSION])
        packages[FakeRegistry.name(service)] = package
        images[service] = image
    if frontend_version_digest:
        other = FakeImage("frontend", layers=(301, 700))
        packages[FakeRegistry.name("frontend")].manifests.update(other.manifests)
        packages[FakeRegistry.name("frontend")].blobs.update(other.blobs)
        packages[FakeRegistry.name("frontend")].tags[VERSION] = other.top
    return FakeRegistry(packages), images


# --- Evidence documents ---

def gate_evidence(**overrides):
    from deploy.rag_delivery.gate import trim_check_run, trim_job, trim_run
    evidence = {
        "schema_version": 1, "repository": REPOSITORY, "event": "push", "tag": VERSION,
        "app_version": APP_VERSION, "commit_sha": SHA, "tag_object_sha": TAG_OBJECT_SHA,
        "captured_at": "2026-10-19T08:00:00Z",
        "gate_run": {"run_id": str(RELEASE_RUN_ID), "run_attempt": "1",
                     "workflow_ref": push_env()["GITHUB_WORKFLOW_REF"]},
        "on_main": True,
        "daily_ci": {"workflow_run": trim_run(ci_run()), "jobs": [trim_job(j) for j in all_jobs()]},
        "check_runs": [trim_check_run(c) for c in all_check_runs()],
        "required_checks": {name: {"check_run_id": CHECK_IDS[name], "conclusion": "success"}
                            for name in REQUIRED_CHECKS},
        "published_release": "absent",
        "ghcr": {"query": "anonymous", "absence_confirmed": False, "note": "x",
                 "tags": [{"repository": IMAGE_REPOSITORIES[s], "tag": t, "state": "UNKNOWN",
                           "detail": "denied", "authenticated": False, "digest": None}
                          for s in ("backend", "frontend") for t in (SHA_TAG, VERSION)]},
        "delivery_checks": [{"command": "python3 -m unittest discover deploy/tests",
                             "source_sha": SHA, "result": "passed"}],
    }
    evidence.update(overrides)
    return evidence


def build_evidence(**overrides):
    evidence = {
        "schema_version": 1, "tag": VERSION, "app_version": APP_VERSION, "commit_sha": SHA,
        "build": {
            "release_run_id": RELEASE_RUN_ID, "run_attempt": 1,
            "workflow_ref": push_env()["GITHUB_WORKFLOW_REF"],
            "runner": "Linux/X64 ubuntu24 20261012.1", "docker_version": "29.1.0",
            "built_at": "2026-10-19T08:10:00Z",
        },
        "inputs": {
            "base_images": {"python:3.13-slim": "sha256:" + "1" * 64,
                            "node:24-alpine": "sha256:" + "2" * 64,
                            "caddy:2-alpine": "sha256:" + "3" * 64},
            "models": {
                "embedding": {"id": "sentence-transformers/all-MiniLM-L6-v2",
                              "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"},
                "reranker": {"id": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                             "revision": "233902d25c440f23af6f7d6e94d2946bac0bee0a"},
            },
            "files": {path: f"{i:064x}" for i, path in enumerate((
                "Backend/Dockerfile", "Frontend/Dockerfile", "Backend/requirements.lock",
                "Frontend/package-lock.json", "Frontend/Caddyfile"), start=1)},
        },
        "data_compat": {
            "declared_schema_fingerprint": "sha256:" + "4" * 64,
            "embedding": {"id": "sentence-transformers/all-MiniLM-L6-v2",
                          "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"},
            "data_format_version": 1,
        },
        "images": {
            "backend": {"uncompressed_size_bytes": 3500000000},
            "frontend": {"uncompressed_size_bytes": 60000000},
        },
    }
    evidence.update(overrides)
    return evidence


def registry_images():
    from deploy.rag_delivery.registry import RegistryClient, resolve_release_images
    registry, _ = published_registry()
    return resolve_release_images(RegistryClient(registry, credentials=("actor", "token")), VERSION, SHA)


def valid_manifest():
    from deploy.rag_delivery.manifest import build_manifest
    return build_manifest(gate_evidence(), build_evidence(), registry_images())


def mutate(document, path, value=None, delete=False):
    """Return a deep copy with ``path`` (dotted string or key tuple) replaced or deleted."""
    keys = path.split(".") if isinstance(path, str) else list(path)
    result = copy.deepcopy(document)
    target = result
    for key in keys[:-1]:
        target = target[key]
    if delete:
        del target[keys[-1]]
    else:
        target[keys[-1]] = value
    return result


def leaf_paths(document, prefix=()):
    """Every key path (as tuples) in a nested dict, parents included."""
    for key, value in document.items():
        path = prefix + (key,)
        if isinstance(value, dict):
            yield from leaf_paths(value, path)
        yield path


def quiet(func, *args, **kwargs):
    """Call ``func`` with its progress output suppressed."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)
