import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from deploy.rag_delivery.__main__ import main
from deploy.rag_delivery.contract import REPOSITORY
from deploy.rag_delivery.manifest import ManifestError, build_manifest, manifest_errors
from deploy.rag_delivery.preview import (
    FORBIDDEN_KEYS,
    PENDING_UNTIL_PUSH,
    PreviewError,
    build_preview,
    preview_errors,
)
from support import (
    APP_VERSION,
    RELEASE_RUN_ID,
    SHA,
    SHA_TAG,
    VERSION,
    build_evidence,
    gate_evidence,
    mutate,
    registry_images,
)

DISPATCH_REF = f"{REPOSITORY}/.github/workflows/release.yml@refs/heads/main"


def labels(service, version=APP_VERSION, sha=SHA):
    return {
        "org.opencontainers.image.source": "https://github.com/Henric0612/rag-news-intelligence-platform",
        "org.opencontainers.image.version": version,
        "org.opencontainers.image.revision": sha,
        "org.opencontainers.image.title": f"rag-news-{service}",
    }


def dispatch_gate(**overrides):
    evidence = gate_evidence(event="workflow_dispatch", tag_object_sha=None,
                             gate_run={"run_id": str(RELEASE_RUN_ID), "run_attempt": "1",
                                       "workflow_ref": DISPATCH_REF})
    evidence.update(overrides)
    return evidence


def dry_run_build(**overrides):
    evidence = build_evidence()
    evidence["build"]["workflow_ref"] = DISPATCH_REF
    for service, size in (("backend", 3500000000), ("frontend", 60000000)):
        evidence["images"][service] = {
            "repository": f"ghcr.io/henric0612/rag-news-{service}",
            "local_tags": [f"ghcr.io/henric0612/rag-news-{service}:{SHA_TAG}",
                           f"ghcr.io/henric0612/rag-news-{service}:{VERSION}"],
            "image_id": f"sha256:{service[0] * 64}",
            "uncompressed_size_bytes": size,
            "platform": "linux/amd64",
            "labels": labels(service),
            "content_check": {"violations": []},
        }
    evidence.update(overrides)
    return evidence


def layer_doc(**overrides):
    doc = {
        "schema_version": 1, "kind": "image-layers", "tag": VERSION, "commit_sha": SHA,
        "measurement": {"method": "docker history --no-trunc --human=false --format {{json .}} <image>",
                        "unit": "bytes"},
        "images": {service: {"image_id": f"sha256:{service[0] * 64}", "max_local_layer_bytes": size,
                             "history_total_bytes": size * 3, "nonzero_layer_count": 5}
                   for service, size in (("backend", 1775644672), ("frontend", 51970048))},
    }
    doc.update(overrides)
    return doc


def run_cli(args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return main(args)


def valid_preview():
    return build_preview(dispatch_gate(), dry_run_build(), layer_doc())


def keys_anywhere(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys_anywhere(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys_anywhere(child)


class PreviewStructureTest(unittest.TestCase):
    def test_valid_preview_carries_verifiable_dry_run_evidence(self):
        preview = valid_preview()
        self.assertEqual(preview_errors(preview), [])
        self.assertEqual(preview["kind"], "release-preview")
        self.assertIs(preview["deployable"], False)
        self.assertIs(preview["release_evidence"], False)
        self.assertIn("not deployable", preview["statement"])
        self.assertEqual((preview["tag"], preview["commit_sha"]), (VERSION, SHA))
        self.assertEqual(preview["gate"]["event"], "workflow_dispatch")
        self.assertEqual(preview["gate"]["gate_run_id"], RELEASE_RUN_ID)
        self.assertEqual(set(preview["gate"]["required_checks"]),
                         {"backend-contracts", "frontend-contracts", "frontend-image", "compose-config"})
        self.assertEqual(preview["inputs"], dry_run_build()["inputs"])
        self.assertEqual(preview["data_compat"], dry_run_build()["data_compat"])
        self.assertEqual(preview["local_images"]["backend"]["local_layers"]["max_local_layer_bytes"], 1775644672)

    def test_preview_contains_no_registry_or_tag_object_evidence(self):
        preview = valid_preview()
        found = set(keys_anywhere(preview)) & FORBIDDEN_KEYS
        self.assertEqual(found, set())
        text = json.dumps(preview)
        self.assertNotIn("@sha256:", text)  # no repository@digest reference
        pending = {item["field"] for item in preview["pending_until_push"]}
        self.assertIn("tag_object_sha", pending)
        for service in ("backend", "frontend"):
            for name in ("digest", "ref", "tags", "media_type", "compressed_size_bytes", "max_layer_bytes"):
                self.assertIn(f"images.{service}.{name}", pending)
        self.assertEqual(preview["pending_until_push"], list(PENDING_UNTIL_PUSH))

    def test_injected_registry_fields_are_rejected(self):
        digest = "sha256:" + "a" * 64
        for path, value in [
            ("tag_object_sha", "0" * 40),
            ("images", {"backend": {"digest": digest}}),
            ("local_images.backend.digest", digest),
            ("local_images.backend.ref", f"ghcr.io/henric0612/rag-news-backend@{digest}"),
            ("local_images.frontend.media_type", "application/vnd.oci.image.index.v1+json"),
            ("local_images.backend.local_layers.max_layer_bytes", 1),
            ("local_images.backend.compressed_size_bytes", 1),
        ]:
            with self.subTest(path=path):
                self.assertTrue(preview_errors(mutate(valid_preview(), path, value)))

    def test_preview_must_declare_itself_non_deployable(self):
        for path, value in [("deployable", True), ("release_evidence", True), ("kind", "release"),
                            ("statement", "ready"), ("pending_until_push", []),
                            ("gate.event", "push"), ("build.release_run_id", 1),
                            ("local_images.backend.labels", labels("backend", version="0.0.0-dev"))]:
            with self.subTest(path=path):
                self.assertTrue(preview_errors(mutate(valid_preview(), path, value)))
        self.assertTrue(preview_errors(mutate(valid_preview(), "pending_until_push", delete=True)))


class PreviewInputsTest(unittest.TestCase):
    def assert_rejected(self, gate, build, layers, message):
        with self.assertRaisesRegex(PreviewError, message):
            build_preview(gate, build, layers)

    def test_only_dispatch_gates_on_main(self):
        self.assert_rejected(gate_evidence(), dry_run_build(), layer_doc(), "only from dispatch")
        self.assert_rejected(dispatch_gate(tag_object_sha="0" * 40), dry_run_build(), layer_doc(), "no tag object")
        build = dry_run_build()
        build["build"]["workflow_ref"] = f"{REPOSITORY}/.github/workflows/release.yml@refs/heads/feature"
        self.assert_rejected(dispatch_gate(), build, layer_doc(), "build.workflow_ref")

    def test_failed_gate_evidence_is_rejected(self):
        gate = dispatch_gate()
        gate["delivery_checks"][0]["result"] = "failed"
        self.assert_rejected(gate, dry_run_build(), layer_doc(), "delivery checks")

    def test_identity_and_image_binding(self):
        self.assert_rejected(dispatch_gate(), dry_run_build(commit_sha="f" * 40), layer_doc(), "build evidence commit_sha")
        self.assert_rejected(dispatch_gate(), dry_run_build(), layer_doc(tag="v0.1.1"), "layer evidence tag")
        layers = layer_doc()
        layers["images"]["frontend"]["image_id"] = "sha256:" + "0" * 64
        self.assert_rejected(dispatch_gate(), dry_run_build(), layers, "frontend: layer evidence image")
        gate = dispatch_gate()
        gate["gate_run"]["run_id"] = "1"
        self.assert_rejected(gate, dry_run_build(), layer_doc(), "release_run_id")


class FormalValidatorRejectsPreviewTest(unittest.TestCase):
    def test_release_manifest_validator_rejects_preview(self):
        errors = manifest_errors(valid_preview())
        self.assertEqual(len(errors), 1)
        self.assertIn("release-preview", errors[0])
        self.assertIn("never release evidence", errors[0])

    def test_preview_relabelled_as_release_is_still_invalid(self):
        self.assertTrue(manifest_errors(mutate(valid_preview(), "kind", "release")))

    def test_release_manifest_builder_refuses_dry_run_gate(self):
        with self.assertRaisesRegex(ManifestError, "tag-push gates"):
            build_manifest(dispatch_gate(), dry_run_build(), registry_images())

    def test_cli_validate_rejects_preview_and_preview_cli_writes_valid_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, doc in (("gate.json", dispatch_gate()), ("build.json", dry_run_build()),
                              ("layers.json", layer_doc())):
                (tmp / name).write_text(json.dumps(doc))
            out = tmp / "release-preview.json"
            code = run_cli(["manifest", "preview", "--gate-evidence", str(tmp / "gate.json"),
                                "--build-evidence", str(tmp / "build.json"),
                                "--layer-evidence", str(tmp / "layers.json"), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(preview_errors(json.loads(out.read_text())), [])
            self.assertEqual(run_cli(["manifest", "validate", "--manifest", str(out)]), 1)

    def test_cli_preview_failure_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, doc in (("gate.json", gate_evidence()), ("build.json", dry_run_build()),
                              ("layers.json", layer_doc())):
                (tmp / name).write_text(json.dumps(doc))
            out = tmp / "release-preview.json"
            code = run_cli(["manifest", "preview", "--gate-evidence", str(tmp / "gate.json"),
                                "--build-evidence", str(tmp / "build.json"),
                                "--layer-evidence", str(tmp / "layers.json"), "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
