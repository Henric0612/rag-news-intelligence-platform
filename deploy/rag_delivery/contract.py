"""Release identity constants and format checks shared by the delivery tools."""

import re

PROJECT = "rag-news-intelligence-platform"
REPOSITORY = "Henric0612/rag-news-intelligence-platform"
SOURCE_URL = "https://github.com/Henric0612/rag-news-intelligence-platform"
MAIN_BRANCH = "main"

IMAGE_REPOSITORIES = {
    "backend": "ghcr.io/henric0612/rag-news-backend",
    "frontend": "ghcr.io/henric0612/rag-news-frontend",
}
IMAGE_TITLES = {
    "backend": "rag-news-backend",
    "frontend": "rag-news-frontend",
}
SERVICES = ("backend", "frontend")
PLATFORM = "linux/amd64"

CI_WORKFLOW_PATH = ".github/workflows/ci.yml"
RELEASE_WORKFLOW_PATH = ".github/workflows/release.yml"
REQUIRED_CHECKS = (
    "backend-contracts",
    "frontend-contracts",
    "frontend-image",
    "compose-config",
)
CHECK_APP_SLUG = "github-actions"
CHECK_APP_ID = 15368

BASE_IMAGES = ("python:3.13-slim", "node:24-alpine", "caddy:2-alpine")
INPUT_FILES = (
    "Backend/Dockerfile",
    "Frontend/Dockerfile",
    "Backend/requirements.lock",
    "Frontend/package-lock.json",
    "Frontend/Caddyfile",
)
LLM_MODEL = "qwen3:8b"
DATA_FORMAT_VERSION = 1

MANIFEST_SCHEMA_VERSION = 1
GATE_EVIDENCE_SCHEMA_VERSION = 1
BUILD_EVIDENCE_SCHEMA_VERSION = 1

MANIFEST_NAME = "release-manifest.json"
GATE_EVIDENCE_NAME = "gate-evidence.json"
SUMS_NAME = "SHA256SUMS"
RELEASE_ASSETS = (MANIFEST_NAME, GATE_EVIDENCE_NAME, SUMS_NAME)

VERSION_RE = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
COMMIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
TIMESTAMP_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class ContractError(ValueError):
    """A value violates the release contract."""


def is_version(value):
    return isinstance(value, str) and VERSION_RE.fullmatch(value) is not None


def is_commit_sha(value):
    return isinstance(value, str) and COMMIT_SHA_RE.fullmatch(value) is not None


def is_digest(value):
    return isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None


def is_timestamp(value):
    return isinstance(value, str) and TIMESTAMP_RE.fullmatch(value) is not None


def require_version(value):
    """Return the app version (tag without ``v``) or raise ContractError."""
    if not is_version(value):
        raise ContractError(f"invalid release version {value!r}: expected vX.Y.Z")
    return value[1:]


def require_commit_sha(value):
    if not is_commit_sha(value):
        raise ContractError(
            f"invalid commit SHA {value!r}: expected 40 lowercase hex characters"
        )
    return value


def sha_tag(commit_sha):
    return f"sha-{require_commit_sha(commit_sha)[:7]}"


def push_order(version, commit_sha):
    """Image tags in the frozen push order: ``sha-<7>`` first, then ``vX.Y.Z``."""
    require_version(version)
    return (sha_tag(commit_sha), version)


def identity_label_errors(service, labels, app_version, commit_sha):
    """Compare the approved CD-WP2 OCI identity labels with the release identity."""
    expected = {
        "org.opencontainers.image.source": SOURCE_URL,
        "org.opencontainers.image.version": app_version,
        "org.opencontainers.image.revision": commit_sha,
        "org.opencontainers.image.title": IMAGE_TITLES[service],
    }
    labels = labels or {}
    return [
        f"{service}: label {name}={labels.get(name)!r}, expected {value!r}"
        for name, value in expected.items()
        if labels.get(name) != value
    ]
