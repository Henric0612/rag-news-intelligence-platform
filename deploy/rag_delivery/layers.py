"""Build-side layer sizes of the dry-run images (U8, D1 part), read-only.

``docker history`` reports, for every history entry of a local image, the
size of the filesystem change it created as stored by the local image store.
These are build-side local measurements. They are not registry values: the
compressed transfer size and the manifest layer sizes (``compressed_size_bytes``
and ``max_layer_bytes`` of the release manifest) exist only after a push and
are read back from the registry at R1. Field names here never reuse those
manifest names.
"""

import json

from .build import run_command
from .contract import BUILD_EVIDENCE_SCHEMA_VERSION, SERVICES

LAYERS_SCHEMA_VERSION = 1
HISTORY_COMMAND = ("docker", "history", "--no-trunc", "--human=false", "--format", "{{json .}}")
GHCR_LAYER_LIMIT_BYTES = 10 * 1000 ** 3
MEASUREMENT = {
    "method": " ".join(HISTORY_COMMAND) + " <image>; docker image inspect <image> (.Size, .RootFS.Layers)",
    "unit": "bytes",
    "semantics": ("max_local_layer_bytes is the largest docker history entry: a build-side, local "
                  "layer size as reported by the local image store (an uncompressed filesystem diff for "
                  "the stores observed; the exact meaning depends on image_store, recorded here). "
                  "inspect_size_bytes is docker image inspect .Size. Neither is a registry compressed size."),
    "not_registry_values": ("Registry compressed transfer size and manifest layer sizes "
                            "(release manifest compressed_size_bytes and max_layer_bytes) are measured "
                            "only after push, at R1, by registry read-back."),
    "ghcr_layer_limit_bytes": GHCR_LAYER_LIMIT_BYTES,
    "ghcr_layer_limit_note": ("GHCR documents a 10 GB limit per layer; it applies to the pushed layer, "
                              "which is checked at R1. No pass/fail is derived here."),
}


class LayerError(RuntimeError):
    """Layer data could not be read or does not match the build evidence."""


def parse_history(output):
    entries = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            size = int(row["Size"])
        except (ValueError, KeyError, TypeError) as error:
            raise LayerError(f"unparsable docker history line {line[:120]!r}") from error
        if size < 0:
            raise LayerError(f"negative layer size in docker history: {size}")
        entries.append({"created_by": row.get("CreatedBy", ""), "size_bytes": size})
    if not entries:
        raise LayerError("docker history returned no entries")
    return entries


def summarize(entries):
    nonzero = [e for e in entries if e["size_bytes"] > 0]
    if not nonzero:
        raise LayerError("docker history reports no non-empty layer")
    largest = max(nonzero, key=lambda e: e["size_bytes"])
    return {
        "history_entries": len(entries),
        "nonzero_layer_count": len(nonzero),
        "history_total_bytes": sum(e["size_bytes"] for e in nonzero),
        "max_local_layer_bytes": largest["size_bytes"],
        "max_local_layer_created_by": largest["created_by"],
    }


def image_store(run):
    return {
        "driver": json.loads(run(["docker", "info", "--format", "{{json .Driver}}"])),
        "driver_status": json.loads(run(["docker", "info", "--format", "{{json .DriverStatus}}"])),
    }


def layer_evidence(build_evidence, now, run=run_command):
    """Measure both dry-run images; raise LayerError on any inconsistency."""
    if build_evidence.get("schema_version") != BUILD_EVIDENCE_SCHEMA_VERSION:
        raise LayerError("unsupported build evidence")
    images = {}
    for service in SERVICES:
        built = (build_evidence.get("images") or {}).get(service)
        if not built:
            raise LayerError(f"build evidence has no {service} image")
        tag = built["local_tags"][0]
        inspect = json.loads(run(["docker", "image", "inspect", tag]))[0]
        if inspect.get("Id") != built["image_id"]:
            raise LayerError(f"{tag} is {inspect.get('Id')}, build evidence recorded {built['image_id']}")
        history = parse_history(run(list(HISTORY_COMMAND) + [tag]))
        images[service] = dict(
            local_tag=tag,
            image_id=built["image_id"],
            inspect_size_bytes=inspect["Size"],
            rootfs_layer_count=len((inspect.get("RootFS") or {}).get("Layers") or []),
            **summarize(history),
            history=history,
        )
        print(f"{service}: {images[service]['nonzero_layer_count']} non-empty layers, largest "
              f"{images[service]['max_local_layer_bytes']} bytes (local, uncompressed)")
    return {
        "schema_version": LAYERS_SCHEMA_VERSION,
        "kind": "image-layers",
        "tag": build_evidence["tag"],
        "commit_sha": build_evidence["commit_sha"],
        "measured_at": now(),
        "image_store": image_store(run),
        "measurement": dict(MEASUREMENT),
        "images": images,
    }
