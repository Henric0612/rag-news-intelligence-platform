"""Static checks of the release workflow's dispatch (dry-run) path; stdlib only, no YAML parser."""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (REPO_ROOT / ".github/workflows/release.yml").read_text()
WRITE_IF = "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"


def jobs():
    """Map each job name to its text block (lines indented under ``jobs:``)."""
    body = WORKFLOW.split("\njobs:\n", 1)[1]
    blocks, name = {}, None
    for line in body.splitlines():
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line)
        if match:
            name = match.group(1)
            blocks[name] = []
        elif name:
            blocks[name].append(line)
    return {k: "\n".join(v) for k, v in blocks.items()}


def permissions(block):
    lines = block.splitlines()
    start = lines.index("    permissions:")
    granted = []
    for line in lines[start + 1:]:
        if not line.startswith("      ") or line.strip().startswith("-"):
            break
        granted.append(line.strip())
    return granted


class DispatchPathTest(unittest.TestCase):
    def test_top_level_permissions_are_empty(self):
        self.assertIn("\npermissions: {}\n", WORKFLOW)

    def test_only_gate_and_build_dry_run_can_run_on_dispatch(self):
        blocks = jobs()
        self.assertEqual(set(blocks), {"gate", "build-push", "build-dry-run", "release"})
        self.assertIn("    if: github.event_name == 'workflow_dispatch'", blocks["build-dry-run"])
        for name in ("build-push", "release"):
            self.assertIn(f"    {WRITE_IF}", blocks[name])

    def test_build_dry_run_has_no_publishing_write_access(self):
        block = jobs()["build-dry-run"]
        self.assertEqual(permissions(block), ["contents: read"])
        for forbidden in ("packages: write", "contents: write", "id-token", "attestations",
                          "docker push", "docker login", "gh release", "secrets.", "github.token",
                          "GITHUB_TOKEN", "deploy.rag_delivery push", "release-draft", "release-publish",
                          "continue-on-error"):
            self.assertNotIn(forbidden, block, forbidden)

    def test_dry_run_evidence_steps_are_ordered_and_uploaded(self):
        block = jobs()["build-dry-run"]
        order = ["public-probe --out", "deploy.rag_delivery build", "deploy.rag_delivery layers",
                 "deploy.rag_delivery license-inventory", "manifest preview"]
        positions = [block.index(step) for step in order]
        self.assertEqual(positions, sorted(positions))
        for artifact in ("dry-run-build-evidence", "dry-run-public-ghcr-probe", "dry-run-image-layers",
                         "dry-run-license-inventory", "dry-run-release-preview"):
            self.assertIn(f"name: {artifact}", block)
        self.assertEqual(block.count("if-no-files-found: error"), 5)
        self.assertEqual(block.count("overwrite: true"), 5)  # a rerun of the job replaces its artifacts
        self.assertIn("name: gate-evidence", block)

    def test_write_jobs_do_not_run_the_dry_run_evidence_steps(self):
        blocks = jobs()
        for name in ("gate", "build-push", "release"):
            for step in ("public-probe", "license-inventory", "manifest preview", "deploy.rag_delivery layers"):
                self.assertNotIn(step, blocks[name])


if __name__ == "__main__":
    unittest.main()
