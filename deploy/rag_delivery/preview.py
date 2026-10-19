"""Release preview (``kind: release-preview``): a dry-run summary, never a release.

A preview carries the verifiable parts of a future release manifest that a
dispatch dry run can actually produce: identity, gate evidence, build inputs,
data compatibility and the locally built images. Everything that exists only
after a protected tag is pushed and the images are in the registry (registry
digest, ref and tags, media type, compressed and manifest layer sizes, the
annotated tag object) is absent and listed in ``pending_until_push`` instead
of being filled with placeholder values.

The release manifest validator rejects every preview (manifest.py), and
``preview_errors`` rejects any preview that claims registry evidence.
"""

from .contract import (
    LLM_MODEL,
    MAIN_BRANCH,
    PREVIEW_KIND,
    PREVIEW_SCHEMA_VERSION,
    PROJECT,
    RELEASE_WORKFLOW_PATH,
    REPOSITORY,
    SERVICES,
    identity_label_errors,
    is_commit_sha,
    is_version,
)
from .gate import gate_evidence_errors, gate_summary
from .manifest import BOOL, INT, SPEC, STR, _check_spec, _positive

PREVIEW_NAME = "release-preview.json"
STATEMENT = ("Dry-run preview. Not a release manifest, not deployable, and not evidence that any "
             "release is COMPLETE. Registry and tag-object fields are pending until a protected tag "
             "push; the tag-push run reruns the gate and rebuilds the images.")
_REGISTRY_FIELDS = ("digest", "ref", "tags", "media_type", "compressed_size_bytes", "max_layer_bytes")
PENDING_UNTIL_PUSH = tuple(
    [{"field": "tag_object_sha", "reason": "the annotated release tag does not exist before the tag push"}]
    + [{"field": f"images.{service}.{name}",
        "reason": "registry value, read back from GHCR only after the tag-push run pushes the image"}
       for service in SERVICES for name in _REGISTRY_FIELDS]
)
REPRODUCED_BY_TAG_RUN = ("gate", "build", "inputs", "data_compat", "images.backend.uncompressed_size_bytes",
                         "images.frontend.uncompressed_size_bytes")
# Keys a preview must never contain at any depth: they would read as registry
# or release evidence. ``images`` is the release manifest group name.
FORBIDDEN_KEYS = frozenset({"images", "tag_object_sha", "digest", "ref", "media_type",
                            "compressed_size_bytes", "max_layer_bytes"})

_LOCAL_LAYERS = {
    "max_local_layer_bytes": (INT, _positive),
    "history_total_bytes": (INT, _positive),
    "nonzero_layer_count": (INT, _positive),
    "measurement": (STR, None),
    "unit": (STR, None),
}
_LOCAL_IMAGE = {
    "repository": (STR, None),
    "local_tags": (list, None),
    "image_id": (STR, None),
    "platform": (STR, None),
    "uncompressed_size_bytes": (INT, _positive),
    "labels": (dict, None),
    "local_layers": _LOCAL_LAYERS,
}
PREVIEW_SPEC = {
    "schema_version": (INT, None),
    "kind": (STR, None),
    "deployable": (BOOL, None),
    "release_evidence": (BOOL, None),
    "statement": (STR, None),
    "project": (STR, None),
    "repository": (STR, None),
    "tag": (STR, is_version),
    "app_version": (STR, None),
    "commit_sha": (STR, is_commit_sha),
    "gate": dict(SPEC["gate"], event=(STR, None), gate_run_id=(INT, _positive)),
    "build": SPEC["build"],
    "inputs": SPEC["inputs"],
    "data_compat": SPEC["data_compat"],
    "external": SPEC["external"],
    "local_images": {service: _LOCAL_IMAGE for service in SERVICES},
    "pending_until_push": (list, None),
    "reproduced_by_tag_run": (list, None),
}
DRY_RUN_WORKFLOW_REF = f"{REPOSITORY}/{RELEASE_WORKFLOW_PATH}@refs/heads/{MAIN_BRANCH}"


class PreviewError(ValueError):
    """The preview or its inputs violate the preview contract."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _forbidden_keys(value, path, errors):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_KEYS:
                errors.append(f"{child_path}: registry or release field is not allowed in a preview")
            if child_path.endswith(".labels"):
                continue  # free-form OCI label names
            _forbidden_keys(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _forbidden_keys(child, f"{path}[{index}]", errors)


def preview_errors(preview):
    """Return every preview contract violation (empty list means a valid preview)."""
    if not isinstance(preview, dict):
        return ["<root>: expected object"]
    errors = []
    _forbidden_keys(preview, "", errors)
    _check_spec(preview, PREVIEW_SPEC, "", errors)
    if errors:
        return errors
    p = preview
    expect = [
        ("schema_version", p["schema_version"], PREVIEW_SCHEMA_VERSION),
        ("kind", p["kind"], PREVIEW_KIND),
        ("deployable", p["deployable"], False),
        ("release_evidence", p["release_evidence"], False),
        ("statement", p["statement"], STATEMENT),
        ("project", p["project"], PROJECT),
        ("repository", p["repository"], REPOSITORY),
        ("app_version", p["app_version"], p["tag"][1:]),
        ("gate.event", p["gate"]["event"], "workflow_dispatch"),
        ("gate.on_main", p["gate"]["on_main"], True),
        ("build.workflow_ref", p["build"]["workflow_ref"], DRY_RUN_WORKFLOW_REF),
        ("build.release_run_id", p["build"]["release_run_id"], p["gate"]["gate_run_id"]),
        ("external.llm_model", p["external"]["llm_model"], LLM_MODEL),
        ("pending_until_push", p["pending_until_push"], list(PENDING_UNTIL_PUSH)),
        ("reproduced_by_tag_run", p["reproduced_by_tag_run"], list(REPRODUCED_BY_TAG_RUN)),
    ]
    for path, actual, wanted in expect:
        if actual != wanted:
            errors.append(f"{path}: {actual!r} != expected {wanted!r}")
    for name, check in p["gate"]["required_checks"].items():
        if check["conclusion"] != "success":
            errors.append(f"gate.required_checks.{name}.conclusion: {check['conclusion']!r}")
    for service in SERVICES:
        image = p["local_images"][service]
        errors += identity_label_errors(service, image["labels"], p["app_version"], p["commit_sha"])
        layers = image["local_layers"]
        if layers["max_local_layer_bytes"] > layers["history_total_bytes"]:
            errors.append(f"local_images.{service}.local_layers: max exceeds total")
    return errors


def build_preview(gate_evidence, build_evidence, layer_evidence):
    """Assemble and validate a preview from dry-run gate, build and layer evidence."""
    errors = gate_evidence_errors(gate_evidence)
    if gate_evidence.get("event") != "workflow_dispatch":
        errors.append("gate evidence: previews come only from dispatch dry runs")
    if gate_evidence.get("tag_object_sha") is not None:
        errors.append("gate evidence: a dry-run gate has no tag object")
    identity = ("tag", "app_version", "commit_sha")
    for name, document in (("build", build_evidence), ("layer", layer_evidence)):
        for key in identity:
            if key in document and document[key] != gate_evidence.get(key):
                errors.append(f"{name} evidence {key} {document[key]!r} != gate evidence {gate_evidence.get(key)!r}")
    try:
        gate_run_id = int((gate_evidence.get("gate_run") or {}).get("run_id"))
    except (TypeError, ValueError):
        gate_run_id = None
        errors.append("gate evidence: gate_run.run_id is missing")
    if errors:
        raise PreviewError(errors)

    local_images = {}
    for service in SERVICES:
        built = build_evidence["images"][service]
        measured = layer_evidence["images"][service]
        if measured["image_id"] != built["image_id"]:
            raise PreviewError([f"{service}: layer evidence image {measured['image_id']} != "
                                f"build evidence image {built['image_id']}"])
        local_images[service] = {
            "repository": built["repository"],
            "local_tags": list(built["local_tags"]),
            "image_id": built["image_id"],
            "platform": built["platform"],
            "uncompressed_size_bytes": built["uncompressed_size_bytes"],
            "labels": dict(built["labels"]),
            "local_layers": {
                "max_local_layer_bytes": measured["max_local_layer_bytes"],
                "history_total_bytes": measured["history_total_bytes"],
                "nonzero_layer_count": measured["nonzero_layer_count"],
                "measurement": layer_evidence["measurement"]["method"],
                "unit": layer_evidence["measurement"]["unit"],
            },
        }
    gate = gate_summary(gate_evidence)
    gate.update(event=gate_evidence["event"], gate_run_id=gate_run_id)
    preview = {
        "schema_version": PREVIEW_SCHEMA_VERSION,
        "kind": PREVIEW_KIND,
        "deployable": False,
        "release_evidence": False,
        "statement": STATEMENT,
        "project": PROJECT,
        "repository": REPOSITORY,
        "tag": gate_evidence["tag"],
        "app_version": gate_evidence["app_version"],
        "commit_sha": gate_evidence["commit_sha"],
        "gate": gate,
        "build": dict(build_evidence["build"]),
        "inputs": build_evidence["inputs"],
        "data_compat": build_evidence["data_compat"],
        "external": {"llm_model": LLM_MODEL},
        "local_images": local_images,
        "pending_until_push": [dict(item) for item in PENDING_UNTIL_PUSH],
        "reproduced_by_tag_run": list(REPRODUCED_BY_TAG_RUN),
    }
    errors = preview_errors(preview)
    if errors:
        raise PreviewError(errors)
    return preview
