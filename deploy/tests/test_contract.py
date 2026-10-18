import unittest

from deploy.rag_delivery.contract import (
    ContractError,
    identity_label_errors,
    is_digest,
    push_order,
    require_commit_sha,
    require_version,
    sha_tag,
)
from support import APP_VERSION, SHA, SHA_TAG, VERSION


class VersionTagTest(unittest.TestCase):
    def test_accepts_plain_semver_tags(self):
        for tag, app in [("v0.1.0", "0.1.0"), ("v1.2.3", "1.2.3"), ("v10.0.20", "10.0.20"), ("v0.0.0", "0.0.0")]:
            with self.subTest(tag=tag):
                self.assertEqual(require_version(tag), app)

    def test_rejects_invalid_tags(self):
        invalid = [
            "", "0.1.0", "V0.1.0", "v0.1", "v0.1.0.0", "v01.0.0", "v0.01.0", "v0.1.00",
            "v0.1.0-rc.1", "v0.1.0+build", "v0.1.0\n", " v0.1.0", "v0.1.0 ", "vX.Y.Z",
            "refs/tags/v0.1.0", "v-1.0.0", "v0.1.0/../x", None, 1,
        ]
        for tag in invalid:
            with self.subTest(tag=tag):
                with self.assertRaises(ContractError):
                    require_version(tag)


class CommitShaTest(unittest.TestCase):
    def test_accepts_full_lowercase_sha(self):
        self.assertEqual(require_commit_sha(SHA), SHA)
        self.assertEqual(sha_tag(SHA), SHA_TAG)

    def test_rejects_short_uppercase_or_non_hex(self):
        for value in [SHA[:7], SHA[:39], SHA + "0", SHA.upper(), "g" * 40, "", None, SHA + "\n"]:
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    require_commit_sha(value)

    def test_push_order_is_sha_tag_then_version(self):
        self.assertEqual(push_order(VERSION, SHA), (SHA_TAG, VERSION))

    def test_digest_format(self):
        self.assertTrue(is_digest("sha256:" + "a" * 64))
        for value in ["sha256:" + "a" * 63, "sha512:" + "a" * 64, "sha256:" + "A" * 64, "a" * 64]:
            self.assertFalse(is_digest(value))


class IdentityLabelTest(unittest.TestCase):
    def labels(self, **overrides):
        labels = {
            "org.opencontainers.image.source": "https://github.com/Henric0612/rag-news-intelligence-platform",
            "org.opencontainers.image.version": APP_VERSION,
            "org.opencontainers.image.revision": SHA,
            "org.opencontainers.image.title": "rag-news-backend",
        }
        labels.update(overrides)
        return labels

    def test_matching_labels_pass(self):
        self.assertEqual(identity_label_errors("backend", self.labels(), APP_VERSION, SHA), [])

    def test_mismatches_are_reported(self):
        cases = {
            "org.opencontainers.image.version": "0.0.0-dev",
            "org.opencontainers.image.revision": "unknown",
            "org.opencontainers.image.title": "rag-news-frontend",
            "org.opencontainers.image.source": "https://example.invalid/fork",
        }
        for name, value in cases.items():
            with self.subTest(label=name):
                errors = identity_label_errors("backend", self.labels(**{name: value}), APP_VERSION, SHA)
                self.assertEqual(len(errors), 1)
                self.assertIn(name, errors[0])

    def test_missing_labels_fail(self):
        self.assertEqual(len(identity_label_errors("frontend", None, APP_VERSION, SHA)), 4)


if __name__ == "__main__":
    unittest.main()
