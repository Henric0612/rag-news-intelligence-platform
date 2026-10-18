import json
import unittest

from deploy.rag_delivery.contract import GATE_EVIDENCE_NAME, MANIFEST_NAME
from deploy.rag_delivery.manifest import (
    ManifestError,
    build_manifest,
    companion_errors,
    manifest_errors,
    render_sums,
    sums_errors,
    validate_manifest,
)
from support import (
    SHA,
    SHA_TAG,
    VERSION,
    build_evidence,
    gate_evidence,
    leaf_paths,
    mutate,
    registry_images,
    valid_manifest,
)


class ValidManifestTest(unittest.TestCase):
    def test_built_manifest_is_valid(self):
        manifest = valid_manifest()
        self.assertEqual(manifest_errors(manifest), [])
        self.assertEqual(manifest["kind"], "release")
        self.assertEqual(manifest["images"]["backend"]["tags"], [VERSION, SHA_TAG])
        self.assertEqual(manifest["images"]["backend"]["uncompressed_size_bytes"], 3500000000)
        self.assertEqual(manifest["gate"]["verified_at"], "2026-10-19T08:00:00Z")
        self.assertEqual(manifest["external"], {"llm_model": "qwen3:8b"})
        self.assertIs(validate_manifest(manifest), manifest)

    def test_round_trips_through_json(self):
        self.assertEqual(manifest_errors(json.loads(json.dumps(valid_manifest()))), [])


class RequiredFieldsTest(unittest.TestCase):
    def test_every_field_is_required(self):
        manifest = valid_manifest()
        for path in leaf_paths(manifest):
            with self.subTest(path=".".join(path)):
                self.assertTrue(manifest_errors(mutate(manifest, path, delete=True)))

    def test_unknown_fields_rejected(self):
        manifest = valid_manifest()
        for path in [("extra",), ("gate", "extra"), ("images", "backend", "extra"), ("images", "sidecar")]:
            with self.subTest(path=path):
                errors = manifest_errors(mutate(manifest, path, "x"))
                self.assertTrue(any("unknown field" in e for e in errors), errors)

    def test_wrong_types_rejected(self):
        manifest = valid_manifest()
        cases = [
            (("schema_version",), "1"), (("schema_version",), True), (("gate", "daily_ci", "run_id"), "39165857610"),
            (("gate", "daily_ci", "run_attempt"), 1.0), (("gate", "on_main"), "true"), (("gate", "on_main"), 1),
            (("images", "backend", "tags"), "v0.1.0"), (("images", "frontend", "compressed_size_bytes"), "1000"),
            (("images", "frontend", "max_layer_bytes"), True), (("build", "release_run_id"), None),
            (("inputs", "files"), []), (("data_compat", "data_format_version"), "1"), (("gate",), []),
            (("commit_sha",), 123), (("tag",), ["v0.1.0"]), (("project",), ""),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                self.assertTrue(manifest_errors(mutate(manifest, path, value)))

    def test_non_object_manifest_rejected(self):
        for value in (None, [], "manifest", 1):
            with self.subTest(value=value):
                self.assertTrue(manifest_errors(value))


class KindAndSchemaTest(unittest.TestCase):
    def test_rehearsal_kind_always_rejected(self):
        rehearsal = {"schema_version": 1, "kind": "rehearsal", "images": {}}
        errors = manifest_errors(rehearsal)
        self.assertEqual(len(errors), 1)
        self.assertIn("rehearsal", errors[0])
        self.assertTrue(manifest_errors(mutate(valid_manifest(), "kind", "rehearsal")))
        with self.assertRaises(ManifestError):
            validate_manifest(rehearsal)

    def test_other_kind_or_schema_rejected(self):
        for path, value in [("kind", "Release"), ("kind", "preview"), ("schema_version", 2), ("schema_version", 0)]:
            with self.subTest(path=path, value=value):
                self.assertTrue(manifest_errors(mutate(valid_manifest(), path, value)))


class IdentityConsistencyTest(unittest.TestCase):
    def assertRejected(self, path, value):
        errors = manifest_errors(mutate(valid_manifest(), path, value))
        self.assertTrue(errors, f"{path}={value!r} accepted")
        return errors

    def test_version_identity(self):
        self.assertRejected("tag", "v0.1")
        self.assertRejected("tag", "0.1.0")
        self.assertRejected("app_version", "0.1.1")
        self.assertRejected("app_version", "v0.1.0")
        self.assertRejected("project", "other-project")
        self.assertRejected("repository", "someone/fork")

    def test_commit_identity(self):
        self.assertRejected("commit_sha", SHA[:7])
        self.assertRejected("commit_sha", SHA.upper())
        self.assertRejected("tag_object_sha", SHA)  # lightweight tag
        self.assertRejected("tag_object_sha", "xyz")

    def test_digest_and_ref(self):
        self.assertRejected("images.backend.digest", "sha256:" + "A" * 64)
        self.assertRejected("images.backend.digest", "sha512:" + "a" * 64)
        manifest = valid_manifest()
        other = "sha256:" + "e" * 64
        errors = manifest_errors(mutate(manifest, "images.backend.digest", other))
        self.assertTrue(any("ref" in e for e in errors), errors)
        self.assertRejected("images.frontend.ref", "ghcr.io/henric0612/rag-news-frontend:v0.1.0")
        self.assertRejected("images.frontend.repository", "ghcr.io/someone/rag-news-frontend")
        same = mutate(manifest, "images.frontend.digest", manifest["images"]["backend"]["digest"])
        same = mutate(same, "images.frontend.ref",
                      f"ghcr.io/henric0612/rag-news-frontend@{manifest['images']['backend']['digest']}")
        self.assertTrue(manifest_errors(same))

    def test_sha_tag_and_version_tag(self):
        self.assertRejected("images.backend.tags", [VERSION, "sha-0000000"])
        self.assertRejected("images.backend.tags", [VERSION])
        self.assertRejected("images.backend.tags", [VERSION, SHA_TAG, "latest"])
        self.assertRejected("images.frontend.tags", ["v0.1.1", SHA_TAG])
        self.assertRejected("images.frontend.tags", [VERSION, VERSION])

    def test_gate_values(self):
        self.assertRejected("gate.daily_ci.event", "pull_request")
        self.assertRejected("gate.daily_ci.head_branch", "feature")
        self.assertRejected("gate.daily_ci.conclusion", "failure")
        self.assertRejected("gate.on_main", False)
        self.assertRejected(("gate", "required_checks", "compose-config", "conclusion"), "failure")
        self.assertRejected("gate.verified_at", "2026-10-19 08:00:00")
        manifest = valid_manifest()
        checks = dict(manifest["gate"]["required_checks"])
        del checks["frontend-image"]
        self.assertTrue(manifest_errors(mutate(manifest, "gate.required_checks", checks)))

    def test_build_and_platform_values(self):
        self.assertRejected("build.workflow_ref",
                            "Henric0612/rag-news-intelligence-platform/.github/workflows/release.yml@refs/heads/main")
        self.assertRejected("build.workflow_ref",
                            "Henric0612/rag-news-intelligence-platform/.github/workflows/release.yml@refs/tags/v0.1.1")
        self.assertRejected("images.backend.platform", "linux/arm64")
        self.assertRejected("images.backend.media_type", "application/json")
        self.assertRejected("images.backend.compressed_size_bytes", 0)
        self.assertRejected("images.backend.max_layer_bytes", 10 ** 12)

    def test_compatibility_key(self):
        self.assertRejected("data_compat.declared_schema_fingerprint", "abc")
        self.assertRejected("data_compat.data_format_version", 2)
        self.assertRejected("data_compat.embedding", {"id": "other", "revision": "1" * 40})
        self.assertRejected(("inputs", "models", "embedding", "revision"), "main")
        self.assertRejected(("inputs", "base_images", "python:3.13-slim"), "python:3.13-slim")
        self.assertRejected(("inputs", "files", "Frontend/Caddyfile"), "not-a-hash")
        self.assertRejected("external.llm_model", "llama3")


class BuildManifestTest(unittest.TestCase):
    def test_rejects_dispatch_gate_evidence(self):
        with self.assertRaisesRegex(ManifestError, "tag-push"):
            build_manifest(gate_evidence(event="workflow_dispatch"), build_evidence(), registry_images())

    def test_rejects_identity_mismatch_between_evidence(self):
        with self.assertRaisesRegex(ManifestError, "identity"):
            build_manifest(gate_evidence(), build_evidence(commit_sha="f" * 40), registry_images())
        with self.assertRaisesRegex(ManifestError, "identity"):
            build_manifest(gate_evidence(), build_evidence(tag="v0.1.1"), registry_images())

    def test_rejects_inconsistent_gate_evidence(self):
        with self.assertRaises(ManifestError):
            build_manifest(gate_evidence(on_main=False), build_evidence(), registry_images())

    def test_rejects_dry_run_build_identity(self):
        evidence = build_evidence()
        evidence["build"]["workflow_ref"] = evidence["build"]["workflow_ref"].replace("refs/tags/v0.1.0", "refs/heads/main")
        with self.assertRaisesRegex(ManifestError, "workflow_ref"):
            build_manifest(gate_evidence(), evidence, registry_images())


class CompanionAssetsTest(unittest.TestCase):
    def files(self):
        manifest = (json.dumps(valid_manifest(), indent=2) + "\n").encode()
        evidence = (json.dumps(gate_evidence(), indent=2) + "\n").encode()
        return {MANIFEST_NAME: manifest, GATE_EVIDENCE_NAME: evidence}

    def test_sums_round_trip(self):
        files = self.files()
        sums = render_sums(files)
        self.assertEqual(sums.splitlines()[0].split("  ")[1], MANIFEST_NAME)
        self.assertEqual(sums_errors(sums, files), [])

    def test_tampered_or_incomplete_sums_rejected(self):
        files = self.files()
        sums = render_sums(files)
        tampered = dict(files)
        tampered[MANIFEST_NAME] = files[MANIFEST_NAME].replace(b"0.1.0", b"0.1.1")
        self.assertTrue(sums_errors(sums, tampered))
        self.assertTrue(sums_errors(sums.splitlines()[0] + "\n", files))
        self.assertTrue(sums_errors(sums + sums.splitlines()[0] + "\n", files))
        self.assertTrue(sums_errors(sums + "0" * 64 + "  extra.json\n", files))
        self.assertTrue(sums_errors(sums.rstrip("\n"), files))
        self.assertTrue(sums_errors(sums.replace("  ", " "), files))
        self.assertTrue(sums_errors(sums, {MANIFEST_NAME: files[MANIFEST_NAME]}))

    def test_manifest_gate_must_match_evidence(self):
        manifest = valid_manifest()
        self.assertEqual(companion_errors(manifest, gate_evidence()), [])
        evidence = gate_evidence()
        evidence["daily_ci"]["workflow_run"]["run_attempt"] = 2
        self.assertTrue(companion_errors(manifest, evidence))
        self.assertTrue(companion_errors(manifest, gate_evidence(commit_sha="f" * 40)))
        self.assertTrue(companion_errors(manifest, gate_evidence(captured_at="2026-10-20T00:00:00Z")))
        evidence = gate_evidence()
        evidence["check_runs"][0]["app_slug"] = "other-app"
        self.assertTrue(companion_errors(manifest, evidence))


if __name__ == "__main__":
    unittest.main()
