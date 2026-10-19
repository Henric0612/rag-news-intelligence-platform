"""Anonymous read probe of a known public GHCR image (U3, D1 logic check).

The release job's anonymous pull check (release.anonymous_pull_errors) cannot
be exercised positively before the first release: the release packages do not
exist or are private. This probe runs the same anonymous RegistryClient path
(token, manifest by digest, OCI index platform selection, config blob through
the storage redirect, platform and labels) against a public, digest-pinned
GHCR image owned by GitHub, and compares every result with values pinned from
a read-only query. Any difference or failure fails the probe.

It shows that the read logic works against real GHCR responses. It does not
show that the release packages are public; R1 provides that evidence
(private: anonymous pull fails; public: it passes).
"""

import urllib.parse

from .contract import PLATFORM
from .registry import INDEX_TYPES, RegistryClient, RegistryError, select_platform_manifest
from .transport import TransportError, urllib_transport

PROBE_SCHEMA_VERSION = 1
# Pinned from an anonymous read-only query of ghcr.io on 2026-10-19
# (tag v0.20.1, published 2025-10-27). The digest, not the tag, is the reference.
PROBE_IMAGE = {
    "repository": "ghcr.io/github/github-mcp-server",
    "digest": "sha256:d909564772c4afc7ed08831c1fce367c051d82f8602abc4c1f033cdfc4a89e68",
    "tag_when_pinned": "v0.20.1",
    "media_type": "application/vnd.oci.image.index.v1+json",
    "platform": PLATFORM,
    "platform_manifest_digest": "sha256:5fa821240fabb7edc5f45e7cf8620d877c19044dba0773fbf819f279f108dadf",
    "config_digest": "sha256:916ede4b2b9012f91f63100f8ba82d07ed81bf8a55d23c1503285a22a9759a1e",
    "labels": {
        "org.opencontainers.image.source": "https://github.com/github/github-mcp-server",
        "org.opencontainers.image.version": "0.20.1",
        "org.opencontainers.image.revision": "0b65b1be52fd345f08e606621896b978ad0ff047",
        "org.opencontainers.image.title": "github-mcp-server",
    },
}
SCOPE_NOTE = ("Validates the anonymous GHCR read logic used by the release job against a known public "
              "image. It is not evidence that the release packages are public or pullable; R1 provides "
              "that (private: anonymous check fails; public: it passes).")


class ProbeError(RuntimeError):
    """The public image probe did not reproduce the pinned results."""


class RecordingTransport:
    """Wrap a transport and record each request without credentials or signed queries."""

    def __init__(self, transport):
        self.transport = transport
        self.requests = []

    def __call__(self, method, url, headers=None, body=None):
        parts = urllib.parse.urlsplit(url)
        authorization = (headers or {}).get("Authorization", "")
        record = {
            "method": method,
            "host": parts.netloc,
            # Token queries carry only the scope; storage redirects carry signatures.
            "path": parts.path + (f"?{parts.query}" if parts.path == "/token" else ""),
            "authorization": authorization.split(" ", 1)[0].lower() if authorization else "none",
        }
        try:
            response = self.transport(method, url, headers, body)
        except TransportError as error:
            record["error"] = str(error)
            self.requests.append(record)
            raise
        record.update(status=response.status,
                      content_type=response.header("content-type"),
                      docker_content_digest=response.header("docker-content-digest"))
        self.requests.append(record)
        return response


def credential_errors(requests, registry_host):
    """Anonymous means: no Basic credentials anywhere, nothing at all sent off the registry host."""
    errors = []
    for r in requests:
        if r["authorization"] == "basic":
            errors.append(f"{r['host']}{r['path']}: credentials sent by an anonymous probe")
        if r["host"] != registry_host and r["authorization"] != "none":
            errors.append(f"{r['host']}: Authorization forwarded off the registry host")
    return errors


def run_probe(now, transport=urllib_transport, image=PROBE_IMAGE):
    """Return (evidence, errors); ``errors`` is empty only if every pinned value matched."""
    recorder = RecordingTransport(transport)
    client = RegistryClient(recorder)  # no credentials: anonymous
    repository, digest = image["repository"], image["digest"]
    observed = {"token": None}
    errors = []
    try:
        token = client.token(repository)
        observed["token"] = "granted" if token else "denied"
        if not token:
            raise ProbeError(f"{repository}: anonymous token denied")
        top_digest, media_type, document = client.resolve(repository, digest, token)
        observed.update(digest=top_digest, media_type=media_type)
        if media_type in INDEX_TYPES:
            observed["platform_manifest_digest"] = select_platform_manifest(document)
        description = client.describe(repository, digest, token)
        observed.update(
            platform=description["platform"],
            config_digest=description["config_digest"],
            labels={k: description["labels"].get(k) for k in image["labels"]},
            registry_compressed_size_bytes=description["compressed_size_bytes"],
            registry_max_layer_bytes=description["max_layer_bytes"],
        )
    except (ProbeError, RegistryError, TransportError, ValueError, KeyError, TypeError, AttributeError) as error:
        # Every failure is recorded, so the evidence file is written on failure too.
        errors.append(f"{type(error).__name__}: {error}")

    if not errors:
        for key in ("digest", "media_type", "platform", "config_digest", "labels"):
            if observed.get(key) != image[key]:
                errors.append(f"{key}: observed {observed.get(key)!r} != pinned {image[key]!r}")
        if image["media_type"] in INDEX_TYPES \
                and observed.get("platform_manifest_digest") != image["platform_manifest_digest"]:
            errors.append(f"platform_manifest_digest: observed {observed.get('platform_manifest_digest')!r} "
                          f"!= pinned {image['platform_manifest_digest']!r}")
    errors += credential_errors(recorder.requests, repository.split("/", 1)[0])

    evidence = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "kind": "public-ghcr-probe",
        "captured_at": now(),
        "reference": f"{repository}@{digest}",
        "pinned": dict(image),
        "anonymous": True,
        "observed": observed,
        "requests": recorder.requests,
        "conclusion": "PASSED" if not errors else "FAILED",
        "errors": errors,
        "scope": SCOPE_NOTE,
    }
    return evidence, errors
