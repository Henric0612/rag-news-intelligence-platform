import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deploy.rag_delivery.__main__ import main
from deploy.rag_delivery.contract import is_digest
from deploy.rag_delivery.public_probe import PROBE_IMAGE, credential_errors, run_probe
from support import FakeImage, FakePackage, FakeRegistry, digest_of

PROBE_NAME = "probe/public-image"


def fake_public(public=True, use_index=True):
    image = FakeImage("frontend", use_index=use_index)
    package = FakePackage(public=public)
    package.put(image, ["v1"])
    pinned = {
        "repository": f"ghcr.io/{PROBE_NAME}",
        "digest": image.top,
        "tag_when_pinned": "v1",
        "media_type": "application/vnd.oci.image.index.v1+json" if use_index
        else "application/vnd.oci.image.manifest.v1+json",
        "platform": "linux/amd64",
        "platform_manifest_digest": digest_of(image.manifest),
        "config_digest": digest_of(image.config),
        "labels": {"org.opencontainers.image.title": "rag-news-frontend",
                   "org.opencontainers.image.version": "0.1.0"},
    }
    return FakeRegistry({PROBE_NAME: package}), pinned


def probe(registry, pinned):
    return run_probe(lambda: "2026-10-19T09:00:00Z", transport=registry, image=pinned)


class PublicProbeTest(unittest.TestCase):
    def test_pinned_reference_is_well_formed(self):
        self.assertEqual(PROBE_IMAGE["repository"], "ghcr.io/github/github-mcp-server")
        for key in ("digest", "platform_manifest_digest", "config_digest"):
            self.assertTrue(is_digest(PROBE_IMAGE[key]), key)
        self.assertEqual(PROBE_IMAGE["platform"], "linux/amd64")
        self.assertEqual(PROBE_IMAGE["media_type"], "application/vnd.oci.image.index.v1+json")
        self.assertTrue(PROBE_IMAGE["labels"])

    def test_anonymous_index_probe_passes_and_records_requests(self):
        registry, pinned = fake_public()
        evidence, errors = probe(registry, pinned)
        self.assertEqual(errors, [])
        self.assertEqual(evidence["conclusion"], "PASSED")
        self.assertEqual(evidence["reference"], f"ghcr.io/{PROBE_NAME}@{pinned['digest']}")
        self.assertEqual(evidence["observed"]["token"], "granted")
        self.assertEqual(evidence["observed"]["platform_manifest_digest"], pinned["platform_manifest_digest"])
        hosts = [(r["host"], r["status"], r["authorization"]) for r in evidence["requests"]]
        self.assertEqual(hosts[0], ("ghcr.io", 200, "none"))
        self.assertIn(("ghcr.io", 307, "bearer"), hosts)
        self.assertEqual(hosts[-1], ("storage.example", 200, "none"))
        self.assertFalse(any("Authorization" in str(r) for r in evidence["requests"]))
        self.assertFalse(any("Basic" in h.get("Authorization", "") for _, _, h in registry.calls))

    def test_single_manifest_probe_passes(self):
        registry, pinned = fake_public(use_index=False)
        self.assertEqual(probe(registry, pinned)[1], [])

    def test_failures_fail_the_probe(self):
        registry, pinned = fake_public()
        cases = {
            "private package (token denied)": (fake_public(public=False)[0], pinned),
            "digest not in registry": (registry, dict(pinned, digest="sha256:" + "0" * 64)),
            "media type differs": (registry, dict(pinned, media_type="application/vnd.oci.image.manifest.v1+json")),
            "platform manifest differs": (registry, dict(pinned, platform_manifest_digest="sha256:" + "1" * 64)),
            "config differs": (registry, dict(pinned, config_digest="sha256:" + "2" * 64)),
            "label differs": (registry, dict(pinned, labels={"org.opencontainers.image.version": "9.9.9"})),
            "network failure": (FakeRegistry(registry.packages, fail_urls=("https://ghcr.io/v2/",)), pinned),
        }
        for name, (transport, image) in cases.items():
            with self.subTest(name):
                evidence, errors = probe(transport, image)
                self.assertTrue(errors)
                self.assertEqual(evidence["conclusion"], "FAILED")
                self.assertEqual(evidence["errors"], errors)

    def test_unexpected_registry_data_is_recorded_as_failure(self):
        registry, pinned = fake_public()
        package = registry.packages[PROBE_NAME]
        package.blobs[pinned["config_digest"]] = b"not json"
        bad = dict(pinned, config_digest=digest_of(b"not json"))
        image = FakeImage("frontend", use_index=True)
        manifest = json.loads(image.manifest)
        manifest["config"]["digest"] = digest_of(b"not json")
        raw = json.dumps(manifest).encode()
        package.manifests[digest_of(raw)] = ("application/vnd.oci.image.manifest.v1+json", raw)
        package.blobs[digest_of(b"not json")] = b"not json"
        evidence, errors = probe(registry, dict(bad, digest=digest_of(raw),
                                                media_type="application/vnd.oci.image.manifest.v1+json"))
        self.assertEqual(evidence["conclusion"], "FAILED")
        self.assertTrue(any(e.startswith(("JSONDecodeError", "ValueError")) for e in errors), errors)

    def test_credential_rules(self):
        self.assertEqual(credential_errors([{"host": "ghcr.io", "path": "/token", "authorization": "none"},
                                            {"host": "ghcr.io", "path": "/v2/x", "authorization": "bearer"}],
                                           "ghcr.io"), [])
        self.assertTrue(credential_errors([{"host": "ghcr.io", "path": "/token", "authorization": "basic"}], "ghcr.io"))
        self.assertTrue(credential_errors([{"host": "storage", "path": "/b", "authorization": "bearer"}], "ghcr.io"))

    def test_cli_failure_writes_evidence_and_exits_nonzero(self):
        registry, pinned = fake_public(public=False)
        failing = probe(registry, pinned)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "public-ghcr-probe.json"
            with mock.patch("deploy.rag_delivery.__main__.run_probe", return_value=failing), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = main(["public-probe", "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.read_text())["conclusion"], "FAILED")


if __name__ == "__main__":
    unittest.main()
