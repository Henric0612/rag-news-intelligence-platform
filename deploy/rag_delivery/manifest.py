"""Release manifest (schema_version 1): construction, validation and companion assets.

This module is the executable form of the manifest contract in
Docs/Phase-E-Delivery.md. ``validate_manifest`` rejects any document that is
not a complete, internally consistent ``kind: release`` manifest, including
every rehearsal manifest.
"""

import hashlib

from .contract import (
    BASE_IMAGES,
    CHECK_APP_SLUG,
    DATA_FORMAT_VERSION,
    GATE_EVIDENCE_NAME,
    IMAGE_REPOSITORIES,
    INPUT_FILES,
    LLM_MODEL,
    MAIN_BRANCH,
    MANIFEST_NAME,
    MANIFEST_SCHEMA_VERSION,
    PLATFORM,
    PREVIEW_KIND,
    PROJECT,
    RELEASE_WORKFLOW_PATH,
    REPOSITORY,
    REQUIRED_CHECKS,
    SERVICES,
    HEX64_RE,
    is_commit_sha,
    is_digest,
    is_timestamp,
    is_version,
    sha_tag,
)
from .gate import gate_evidence_errors, gate_summary
from .registry import MANIFEST_MEDIA_TYPES

# Field specification: a dict maps keys to nested specs; a tuple is
# (type, extra-check-or-None). Unknown keys are rejected at every level.
STR, INT, BOOL = str, int, bool


def _positive(value):
    return value > 0


def _hex64(value):
    return HEX64_RE.fullmatch(value) is not None


_MODEL = {"id": (STR, None), "revision": (STR, is_commit_sha)}
_IMAGE = {
    "repository": (STR, None),
    "digest": (STR, is_digest),
    "ref": (STR, None),
    "tags": (list, None),
    "platform": (STR, None),
    "media_type": (STR, None),
    "compressed_size_bytes": (INT, _positive),
    "uncompressed_size_bytes": (INT, _positive),
    "max_layer_bytes": (INT, _positive),
}
SPEC = {
    "schema_version": (INT, None),
    "kind": (STR, None),
    "project": (STR, None),
    "repository": (STR, None),
    "tag": (STR, is_version),
    "app_version": (STR, None),
    "commit_sha": (STR, is_commit_sha),
    "tag_object_sha": (STR, is_commit_sha),
    "gate": {
        "daily_ci": {
            "run_id": (INT, _positive),
            "run_attempt": (INT, _positive),
            "event": (STR, None),
            "head_branch": (STR, None),
            "conclusion": (STR, None),
        },
        "required_checks": {
            name: {"check_run_id": (INT, _positive), "conclusion": (STR, None)}
            for name in REQUIRED_CHECKS
        },
        "on_main": (BOOL, None),
        "verified_at": (STR, is_timestamp),
    },
    "build": {
        "release_run_id": (INT, _positive),
        "run_attempt": (INT, _positive),
        "workflow_ref": (STR, None),
        "runner": (STR, None),
        "docker_version": (STR, None),
        "built_at": (STR, is_timestamp),
    },
    "images": {service: _IMAGE for service in SERVICES},
    "inputs": {
        "base_images": {name: (STR, is_digest) for name in BASE_IMAGES},
        "models": {"embedding": _MODEL, "reranker": _MODEL},
        "files": {path: (STR, _hex64) for path in INPUT_FILES},
    },
    "data_compat": {
        "declared_schema_fingerprint": (STR, is_digest),
        "embedding": _MODEL,
        "data_format_version": (INT, None),
    },
    "external": {"llm_model": (STR, None)},
}


class ManifestError(ValueError):
    """The manifest or its companion assets violate the release contract."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _type_ok(value, expected):
    if expected is INT:
        return type(value) is int  # bool is not an int here
    return isinstance(value, expected)


def _check_spec(value, spec, path, errors):
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            errors.append(f"{path or '<root>'}: expected object")
            return
        for key in sorted(set(value) - set(spec)):
            errors.append(f"{path}.{key}: unknown field" if path else f"{key}: unknown field")
        for key, sub in spec.items():
            child = f"{path}.{key}" if path else key
            if key not in value:
                errors.append(f"{child}: missing")
            else:
                _check_spec(value[key], sub, child, errors)
        return
    expected, check = spec
    if not _type_ok(value, expected):
        errors.append(f"{path}: expected {expected.__name__}, got {type(value).__name__}")
    elif check is not None and value != "" and not check(value):
        errors.append(f"{path}: invalid value {value!r}")
    elif expected is STR and value == "":
        errors.append(f"{path}: empty string")


def manifest_errors(manifest):
    """Return every contract violation (empty list means valid)."""
    if isinstance(manifest, dict) and manifest.get("kind") == "rehearsal":
        return ["kind: rehearsal manifests are never release evidence; release validator rejects them"]
    if isinstance(manifest, dict) and manifest.get("kind") == PREVIEW_KIND:
        return [f"kind: {PREVIEW_KIND} is a dry-run preview, not deployable and never release evidence; "
                "release validator rejects it"]
    errors = []
    _check_spec(manifest, SPEC, "", errors)
    if errors:
        return errors

    m = manifest
    expect = [
        ("schema_version", m["schema_version"], MANIFEST_SCHEMA_VERSION),
        ("kind", m["kind"], "release"),
        ("project", m["project"], PROJECT),
        ("repository", m["repository"], REPOSITORY),
        ("app_version", m["app_version"], m["tag"][1:]),
        ("gate.daily_ci.event", m["gate"]["daily_ci"]["event"], "push"),
        ("gate.daily_ci.head_branch", m["gate"]["daily_ci"]["head_branch"], MAIN_BRANCH),
        ("gate.daily_ci.conclusion", m["gate"]["daily_ci"]["conclusion"], "success"),
        ("gate.on_main", m["gate"]["on_main"], True),
        ("build.workflow_ref", m["build"]["workflow_ref"],
         f"{REPOSITORY}/{RELEASE_WORKFLOW_PATH}@refs/tags/{m['tag']}"),
        ("data_compat.embedding", m["data_compat"]["embedding"], m["inputs"]["models"]["embedding"]),
        ("data_compat.data_format_version", m["data_compat"]["data_format_version"], DATA_FORMAT_VERSION),
        ("external.llm_model", m["external"]["llm_model"], LLM_MODEL),
    ]
    for path, actual, wanted in expect:
        if actual != wanted:
            errors.append(f"{path}: {actual!r} != expected {wanted!r}")
    if m["tag_object_sha"] == m["commit_sha"]:
        errors.append("tag_object_sha: equals commit_sha; release tags must be annotated")
    for name, check in m["gate"]["required_checks"].items():
        if check["conclusion"] != "success":
            errors.append(f"gate.required_checks.{name}.conclusion: {check['conclusion']!r}")

    expected_tags = {m["tag"], sha_tag(m["commit_sha"])}
    for service in SERVICES:
        image = m["images"][service]
        prefix = f"images.{service}"
        if image["repository"] != IMAGE_REPOSITORIES[service]:
            errors.append(f"{prefix}.repository: {image['repository']!r} != {IMAGE_REPOSITORIES[service]!r}")
        if image["ref"] != f"{image['repository']}@{image['digest']}":
            errors.append(f"{prefix}.ref: does not equal repository@digest")
        if not all(isinstance(t, str) for t in image["tags"]) or len(image["tags"]) != 2 \
                or set(image["tags"]) != expected_tags:
            errors.append(f"{prefix}.tags: {image['tags']!r} != {sorted(expected_tags)!r}")
        if image["platform"] != PLATFORM:
            errors.append(f"{prefix}.platform: {image['platform']!r} != {PLATFORM!r}")
        if image["media_type"] not in MANIFEST_MEDIA_TYPES:
            errors.append(f"{prefix}.media_type: unsupported {image['media_type']!r}")
        if image["max_layer_bytes"] > image["compressed_size_bytes"]:
            errors.append(f"{prefix}.max_layer_bytes: exceeds compressed_size_bytes")
    if m["images"]["backend"]["digest"] == m["images"]["frontend"]["digest"]:
        errors.append("images: backend and frontend have the same digest")
    return errors


def validate_manifest(manifest):
    errors = manifest_errors(manifest)
    if errors:
        raise ManifestError(errors)
    return manifest


def build_manifest(gate_evidence, build_evidence, registry_images):
    """Assemble a release manifest from gate, build and registry evidence."""
    errors = gate_evidence_errors(gate_evidence)
    if gate_evidence.get("event") != "push":
        errors.append("gate evidence: release manifests come only from tag-push gates")
    if build_evidence.get("commit_sha") != gate_evidence.get("commit_sha") \
            or build_evidence.get("tag") != gate_evidence.get("tag"):
        errors.append("build evidence: identity differs from gate evidence")
    if errors:
        raise ManifestError(errors)

    images = {}
    for service in SERVICES:
        registry = registry_images[service]
        images[service] = {
            "repository": registry["repository"],
            "digest": registry["digest"],
            "ref": registry["ref"],
            "tags": list(registry["tags"]),
            "platform": registry["platform"],
            "media_type": registry["media_type"],
            "compressed_size_bytes": registry["compressed_size_bytes"],
            "uncompressed_size_bytes": build_evidence["images"][service]["uncompressed_size_bytes"],
            "max_layer_bytes": registry["max_layer_bytes"],
        }
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kind": "release",
        "project": PROJECT,
        "repository": REPOSITORY,
        "tag": gate_evidence["tag"],
        "app_version": gate_evidence["app_version"],
        "commit_sha": gate_evidence["commit_sha"],
        "tag_object_sha": gate_evidence["tag_object_sha"],
        "gate": gate_summary(gate_evidence),
        "build": dict(build_evidence["build"]),
        "images": images,
        "inputs": build_evidence["inputs"],
        "data_compat": build_evidence["data_compat"],
        "external": {"llm_model": LLM_MODEL},
    }
    return validate_manifest(manifest)


def companion_errors(manifest, gate_evidence):
    """The manifest gate summary must be derived from the gate-evidence snapshot."""
    errors = list(gate_evidence_errors(gate_evidence))
    for key in ("tag", "app_version", "commit_sha", "tag_object_sha"):
        if gate_evidence.get(key) != manifest.get(key):
            errors.append(f"gate evidence {key} {gate_evidence.get(key)!r} != manifest {manifest.get(key)!r}")
    try:
        if gate_summary(gate_evidence) != manifest.get("gate"):
            errors.append("manifest gate group is not derived from gate evidence")
    except (KeyError, TypeError) as error:
        errors.append(f"gate evidence malformed ({error!r})")
    for name, check in (gate_evidence.get("required_checks") or {}).items():
        for c in gate_evidence.get("check_runs", []):
            if c.get("id") == check.get("check_run_id") and c.get("app_slug") != CHECK_APP_SLUG:
                errors.append(f"gate evidence: {name} not from GitHub Actions")
    return errors


def render_sums(files):
    """SHA256SUMS text for {name: bytes}, in manifest-then-evidence order."""
    return "".join(f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n"
                   for name in (MANIFEST_NAME, GATE_EVIDENCE_NAME))


def sums_errors(sums_text, files):
    """Verify SHA256SUMS lists exactly the two JSON assets with matching hashes."""
    errors = []
    entries = {}
    lines = sums_text.splitlines()
    if not sums_text.endswith("\n"):
        errors.append("SHA256SUMS: missing trailing newline")
    for line in lines:
        digest, sep, name = line.partition("  ")
        if not sep or not _hex64(digest) or not name:
            errors.append(f"SHA256SUMS: malformed line {line!r}")
            continue
        if name in entries:
            errors.append(f"SHA256SUMS: duplicate entry {name}")
        entries[name] = digest
    expected = {MANIFEST_NAME, GATE_EVIDENCE_NAME}
    if set(entries) != expected:
        errors.append(f"SHA256SUMS: entries {sorted(entries)} != {sorted(expected)}")
    for name in expected & set(entries):
        if name not in files:
            errors.append(f"SHA256SUMS: {name} not provided")
        elif hashlib.sha256(files[name]).hexdigest() != entries[name]:
            errors.append(f"SHA256SUMS: {name} checksum mismatch")
    return errors
