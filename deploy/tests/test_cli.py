import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deploy.rag_delivery.contract import GATE_EVIDENCE_NAME, MANIFEST_NAME, SUMS_NAME
from deploy.rag_delivery.manifest import render_sums
from support import gate_evidence, mutate, valid_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    return subprocess.run([sys.executable, "-m", "deploy.rag_delivery", *args], cwd=REPO_ROOT,
                          env=env, capture_output=True, text=True)


class ManifestCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write_assets(self, manifest, evidence=None):
        files = {
            MANIFEST_NAME: (json.dumps(manifest, indent=2) + "\n").encode(),
            GATE_EVIDENCE_NAME: (json.dumps(evidence or gate_evidence(), indent=2) + "\n").encode(),
        }
        for name, data in files.items():
            (self.dir / name).write_bytes(data)
        (self.dir / SUMS_NAME).write_text(render_sums(files))

    def test_valid_manifest_exits_zero(self):
        path = self.dir / "m.json"
        path.write_text(json.dumps(valid_manifest()))
        result = cli("manifest", "validate", "--manifest", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_and_rehearsal_manifests_exit_nonzero(self):
        for name, manifest in {
            "rehearsal": {"schema_version": 1, "kind": "rehearsal"},
            "missing digest": mutate(valid_manifest(), "images.backend.digest", delete=True),
            "sha tag mismatch": mutate(valid_manifest(), "images.backend.tags", ["v0.1.0", "sha-0000000"]),
        }.items():
            with self.subTest(name):
                path = self.dir / "m.json"
                path.write_text(json.dumps(manifest))
                result = cli("manifest", "validate", "--manifest", str(path))
                self.assertEqual(result.returncode, 1)
                self.assertIn("error:", result.stderr)

    def test_assets_dir_validation(self):
        self.write_assets(valid_manifest())
        self.assertEqual(cli("manifest", "validate", "--assets-dir", str(self.dir)).returncode, 0)
        (self.dir / MANIFEST_NAME).write_text((self.dir / MANIFEST_NAME).read_text().replace("0.1.0", "0.1.1"))
        result = cli("manifest", "validate", "--assets-dir", str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("checksum mismatch", result.stderr)

    def test_assets_dir_rejects_mismatched_evidence(self):
        self.write_assets(valid_manifest(), gate_evidence(captured_at="2026-10-20T00:00:00Z"))
        result = cli("manifest", "validate", "--assets-dir", str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("not derived from gate evidence", result.stderr)

    def test_gate_rejects_bad_dispatch_input_before_network(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
        env.update(GITHUB_EVENT_NAME="workflow_dispatch", GITHUB_REF="refs/heads/main", INPUT_SHA="abc", INPUT_VERSION="v0.1.0",
                   GITHUB_TOKEN="unused", GITHUB_REPOSITORY="Henric0612/rag-news-intelligence-platform")
        result = subprocess.run([sys.executable, "-m", "deploy.rag_delivery", "gate", "--source-dir", ".",
                                 "--evidence", str(self.dir / "e.json")],
                                cwd=REPO_ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid commit SHA", result.stderr)
        self.assertFalse((self.dir / "e.json").exists())

    def test_unknown_command_is_usage_error(self):
        self.assertEqual(cli("deploy").returncode, 2)


if __name__ == "__main__":
    unittest.main()
