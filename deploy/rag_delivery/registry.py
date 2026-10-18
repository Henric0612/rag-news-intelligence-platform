"""GHCR reads: tag-state classification, digest resolution and image description.

Tag state is one of three values:

- ``EXISTS``: the registry served the manifest (HTTP 200);
- ``NOT_FOUND``: a token was granted and the registry answered HTTP 404 with
  only ``MANIFEST_UNKNOWN``/``NAME_UNKNOWN`` errors;
- ``UNKNOWN``: anything else, including a denied token, 401/403, ``DENIED``,
  an unparsable response or a network failure.

``UNKNOWN`` is never treated as absence. Anonymous GHCR requests are denied
for both a missing and a private package, so an anonymous ``UNKNOWN`` cannot
prove that a tag is absent.
"""

import base64
import hashlib
import json
import urllib.parse
from dataclasses import asdict, dataclass

from .contract import IMAGE_REPOSITORIES, PLATFORM, SERVICES, push_order
from .transport import TransportError, request_following_redirects, urllib_transport

EXISTS = "EXISTS"
NOT_FOUND = "NOT_FOUND"
UNKNOWN = "UNKNOWN"

NOT_FOUND_CODES = frozenset({"MANIFEST_UNKNOWN", "NAME_UNKNOWN"})
INDEX_TYPES = frozenset({
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
})
IMAGE_MANIFEST_TYPES = frozenset({
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
})
MANIFEST_MEDIA_TYPES = INDEX_TYPES | IMAGE_MANIFEST_TYPES
ACCEPT = ", ".join(sorted(MANIFEST_MEDIA_TYPES))


class RegistryError(RuntimeError):
    """A registry read returned an unexpected or inconsistent result."""


@dataclass(frozen=True)
class TagState:
    repository: str
    tag: str
    state: str
    detail: str
    authenticated: bool
    digest: str = None

    def as_dict(self):
        return asdict(self)


def split_repository(repository):
    host, _, name = repository.partition("/")
    if host != "ghcr.io" or not name:
        raise RegistryError(f"unsupported image repository {repository!r}")
    return host, name


def error_codes(body):
    """Return the set of registry error codes in a response body (empty if unparsable)."""
    try:
        data = json.loads(body or b"null")
    except ValueError:
        return frozenset()
    errors = data.get("errors") if isinstance(data, dict) else None
    if not isinstance(errors, list):
        return frozenset()
    return frozenset(
        e.get("code") for e in errors if isinstance(e, dict) and isinstance(e.get("code"), str)
    )


def classify_tag(token, response):
    """Classify a manifest lookup. ``token`` is None when the token was denied."""
    if token is None:
        return UNKNOWN, "registry token denied (package missing, private or not accessible)"
    if response.status == 200:
        return EXISTS, "manifest served (HTTP 200)"
    codes = error_codes(response.body)
    if response.status == 404 and codes and codes <= NOT_FOUND_CODES:
        return NOT_FOUND, f"HTTP 404 {sorted(codes)}"
    return UNKNOWN, f"HTTP {response.status} {sorted(codes) or 'no error code'}"


def content_digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def parse_manifest_response(response, reference):
    """Validate a 200 manifest response and return (digest, media_type, document)."""
    if response.status != 200:
        raise RegistryError(
            f"manifest {reference}: HTTP {response.status} {sorted(error_codes(response.body))}"
        )
    digest = content_digest(response.body)
    header_digest = response.header("docker-content-digest")
    if header_digest and header_digest != digest:
        raise RegistryError(f"manifest {reference}: header digest {header_digest} != body {digest}")
    if reference.startswith("sha256:") and reference != digest:
        raise RegistryError(f"manifest {reference}: body digest is {digest}")
    try:
        document = json.loads(response.body)
    except ValueError as error:
        raise RegistryError(f"manifest {reference}: invalid JSON") from error
    media_type = (response.header("content-type") or "").split(";", 1)[0].strip()
    body_type = document.get("mediaType")
    if body_type and media_type and body_type != media_type:
        raise RegistryError(f"manifest {reference}: content type {media_type} != {body_type}")
    media_type = media_type or body_type
    if media_type not in MANIFEST_MEDIA_TYPES:
        raise RegistryError(f"manifest {reference}: unsupported media type {media_type!r}")
    return digest, media_type, document


def select_platform_manifest(index):
    """Pick the single linux/amd64 image manifest from an index (attestations excluded)."""
    os_name, arch = PLATFORM.split("/")
    matches = [
        entry for entry in index.get("manifests", [])
        if isinstance(entry, dict)
        and entry.get("platform", {}).get("os") == os_name
        and entry.get("platform", {}).get("architecture") == arch
        and entry.get("mediaType") in IMAGE_MANIFEST_TYPES
    ]
    if len(matches) != 1:
        raise RegistryError(f"index has {len(matches)} {PLATFORM} image manifests, expected 1")
    return matches[0]["digest"]


def summarize_layers(document):
    layers = document.get("layers")
    if not isinstance(layers, list) or not layers:
        raise RegistryError("image manifest has no layers")
    sizes = [layer.get("size") for layer in layers]
    if not all(type(size) is int and size > 0 for size in sizes):
        raise RegistryError("image manifest has an invalid layer size")
    return sum(sizes), max(sizes)


class RegistryClient:
    def __init__(self, transport=urllib_transport, credentials=None):
        self.transport = transport
        self.credentials = credentials

    @property
    def authenticated(self):
        return self.credentials is not None

    def token(self, repository, actions="pull"):
        """Return a bearer token, or None if the registry did not grant one."""
        host, name = split_repository(repository)
        query = urllib.parse.urlencode({"scope": f"repository:{name}:{actions}", "service": host})
        headers = {"User-Agent": "rag-delivery"}
        if self.credentials:
            user, secret = self.credentials
            basic = base64.b64encode(f"{user}:{secret}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
        response = self.transport("GET", f"https://{host}/token?{query}", headers, None)
        if response.status != 200:
            return None
        try:
            data = json.loads(response.body)
        except ValueError:
            return None
        token = (data.get("token") or data.get("access_token")) if isinstance(data, dict) else None
        return token if isinstance(token, str) and token else None

    def manifest(self, repository, reference, token):
        host, name = split_repository(repository)
        headers = {"Accept": ACCEPT, "Authorization": f"Bearer {token}", "User-Agent": "rag-delivery"}
        return self.transport("GET", f"https://{host}/v2/{name}/manifests/{reference}", headers, None)

    def blob(self, repository, digest, token):
        host, name = split_repository(repository)
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "rag-delivery"}
        response = request_following_redirects(
            self.transport, "GET", f"https://{host}/v2/{name}/blobs/{digest}", headers
        )
        if response.status != 200:
            raise RegistryError(f"blob {digest}: HTTP {response.status}")
        if content_digest(response.body) != digest:
            raise RegistryError(f"blob {digest}: content digest mismatch")
        return response.body

    def tag_state(self, repository, tag, actions="pull"):
        try:
            token = self.token(repository, actions)
            response = self.manifest(repository, tag, token) if token else None
        except TransportError as error:
            return TagState(repository, tag, UNKNOWN, f"request failed: {error}", self.authenticated)
        state, detail = classify_tag(token, response)
        digest = None
        if state == EXISTS:
            digest = content_digest(response.body)
        return TagState(repository, tag, state, detail, self.authenticated, digest)

    def resolve(self, repository, reference, token):
        return parse_manifest_response(self.manifest(repository, reference, token), reference)

    def describe(self, repository, digest, token):
        """Describe the image at ``repository@digest`` from registry data only."""
        top_digest, media_type, document = self.resolve(repository, digest, token)
        image_document = document
        if media_type in INDEX_TYPES:
            platform_digest = select_platform_manifest(document)
            _, platform_type, image_document = self.resolve(repository, platform_digest, token)
            if platform_type not in IMAGE_MANIFEST_TYPES:
                raise RegistryError(f"{platform_digest}: not an image manifest")
        compressed, max_layer = summarize_layers(image_document)
        config_digest = image_document.get("config", {}).get("digest")
        config = json.loads(self.blob(repository, config_digest, token))
        platform = f"{config.get('os')}/{config.get('architecture')}"
        if platform != PLATFORM:
            raise RegistryError(f"{repository}@{digest}: platform {platform}, expected {PLATFORM}")
        return {
            "digest": top_digest,
            "media_type": media_type,
            "platform": platform,
            "compressed_size_bytes": compressed,
            "max_layer_bytes": max_layer,
            "config_digest": config_digest,
            "labels": (config.get("config") or {}).get("Labels") or {},
        }


def release_tag_states(client, version, commit_sha, actions="pull"):
    """Look up the four release target tags (two per image)."""
    return [
        client.tag_state(IMAGE_REPOSITORIES[service], tag, actions)
        for service in SERVICES
        for tag in push_order(version, commit_sha)
    ]


def gate_conflicts(states):
    """Gate rule: only EXISTS blocks; UNKNOWN is recorded as unconfirmed, never as absent."""
    return [s for s in states if s.state == EXISTS]


def prepush_blockers(states):
    """Pre-push rule: every target tag must be confirmed NOT_FOUND by an authenticated query."""
    if len(states) != 2 * len(SERVICES):
        return ["expected four target tag lookups"]
    return [
        f"{s.repository}:{s.tag} is {s.state} ({s.detail})"
        for s in states
        if not (s.state == NOT_FOUND and s.authenticated)
    ]


def resolve_release_images(client, version, commit_sha, actions="pull"):
    """Resolve both tags of each image; both must name the same digest."""
    images = {}
    for service in SERVICES:
        repository = IMAGE_REPOSITORIES[service]
        token = client.token(repository, actions)
        if not token:
            raise RegistryError(f"{repository}: registry token denied")
        digests = {}
        for tag in push_order(version, commit_sha):
            digest, _, _ = client.resolve(repository, tag, token)
            digests[tag] = digest
        if len(set(digests.values())) != 1:
            raise RegistryError(f"{repository}: tags resolve to different digests {digests}")
        digest = next(iter(digests.values()))
        description = client.describe(repository, digest, token)
        description.update(
            repository=repository,
            ref=f"{repository}@{digest}",
            tags=[version, push_order(version, commit_sha)[0]],
        )
        images[service] = description
    return images
