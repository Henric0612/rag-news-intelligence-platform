import json
import unittest

from deploy.rag_delivery.registry import (
    EXISTS,
    NOT_FOUND,
    UNKNOWN,
    RegistryClient,
    RegistryError,
    TagState,
    classify_tag,
    gate_conflicts,
    parse_manifest_response,
    prepush_blockers,
    release_tag_states,
    resolve_release_images,
    select_platform_manifest,
)
from deploy.rag_delivery.transport import Response
from support import (
    MEDIA_OCI_MANIFEST,
    SHA,
    SHA_TAG,
    VERSION,
    FakeImage,
    FakePackage,
    FakeRegistry,
    digest_of,
    published_registry,
)

DENIED = b'{"errors":[{"code":"DENIED","message":"requested access to the resource is denied"}]}'


class ClassifyTagTest(unittest.TestCase):
    def test_exists_only_on_200(self):
        self.assertEqual(classify_tag("t", Response(200, {}, b"{}"))[0], EXISTS)

    def test_not_found_requires_token_404_and_unknown_codes(self):
        for body in (b'{"errors":[{"code":"MANIFEST_UNKNOWN"}]}', b'{"errors":[{"code":"NAME_UNKNOWN"}]}',
                     b'{"errors":[{"code":"MANIFEST_UNKNOWN"},{"code":"NAME_UNKNOWN"}]}'):
            with self.subTest(body=body):
                self.assertEqual(classify_tag("t", Response(404, {}, body))[0], NOT_FOUND)

    def test_everything_else_is_unknown(self):
        cases = {
            "token denied": (None, None),
            "403 DENIED": ("t", Response(403, {}, DENIED)),
            "401": ("t", Response(401, {}, b'{"errors":[{"code":"UNAUTHORIZED"}]}')),
            "404 DENIED code": ("t", Response(404, {}, DENIED)),
            "404 mixed codes": ("t", Response(404, {}, b'{"errors":[{"code":"MANIFEST_UNKNOWN"},{"code":"DENIED"}]}')),
            "404 no body": ("t", Response(404, {}, b"")),
            "404 html": ("t", Response(404, {}, b"<html>not found</html>")),
            "429": ("t", Response(429, {}, b'{"errors":[{"code":"TOOMANYREQUESTS"}]}')),
            "500": ("t", Response(500, {}, b"")),
        }
        for name, (token, response) in cases.items():
            with self.subTest(name):
                self.assertEqual(classify_tag(token, response)[0], UNKNOWN)


class TagStateTest(unittest.TestCase):
    def test_anonymous_missing_and_private_packages_are_unknown(self):
        private = FakePackage(public=False)
        private.put(FakeImage("backend"), [SHA_TAG, VERSION])
        registry = RegistryClient(FakeRegistry({FakeRegistry.name("backend"): private}))
        states = release_tag_states(registry, VERSION, SHA)
        self.assertEqual([s.state for s in states], [UNKNOWN] * 4)
        self.assertTrue(all(not s.authenticated for s in states))
        # The gate does not block on UNKNOWN, but it never reports absence either.
        self.assertEqual(gate_conflicts(states), [])
        self.assertEqual(len(prepush_blockers(states)), 4)

    def test_anonymous_public_package(self):
        registry, _ = published_registry(public=True)
        states = release_tag_states(RegistryClient(registry), VERSION, SHA)
        self.assertEqual([s.state for s in states], [EXISTS] * 4)
        self.assertEqual(len(gate_conflicts(states)), 4)
        self.assertTrue(all(s.digest and s.digest.startswith("sha256:") for s in states))

    def test_authenticated_missing_package_is_not_found(self):
        client = RegistryClient(FakeRegistry({}), credentials=("actor", "token"))
        states = release_tag_states(client, VERSION, SHA, actions="pull,push")
        self.assertEqual([s.state for s in states], [NOT_FOUND] * 4)
        self.assertEqual(prepush_blockers(states), [])

    def test_authenticated_denied_is_unknown_and_blocks(self):
        client = RegistryClient(FakeRegistry({}, auth_ok=False), credentials=("actor", "token"))
        states = release_tag_states(client, VERSION, SHA, actions="pull,push")
        self.assertEqual([s.state for s in states], [UNKNOWN] * 4)
        self.assertEqual(len(prepush_blockers(states)), 4)

    def test_authenticated_private_existing_tag_is_exists(self):
        private = FakePackage(public=False)
        private.put(FakeImage("frontend"), [VERSION])
        client = RegistryClient(FakeRegistry({FakeRegistry.name("frontend"): private}),
                                credentials=("actor", "token"))
        states = {(s.repository.rsplit("/", 1)[1], s.tag): s.state
                  for s in release_tag_states(client, VERSION, SHA, actions="pull,push")}
        self.assertEqual(states[("rag-news-frontend", VERSION)], EXISTS)
        self.assertEqual(states[("rag-news-frontend", SHA_TAG)], NOT_FOUND)

    def test_network_failure_is_unknown(self):
        client = RegistryClient(FakeRegistry({}, fail_urls=("https://ghcr.io/token",)),
                                credentials=("actor", "token"))
        states = release_tag_states(client, VERSION, SHA, actions="pull,push")
        self.assertEqual({s.state for s in states}, {UNKNOWN})
        self.assertIn("request failed", states[0].detail)

    def test_prepush_requires_authenticated_not_found(self):
        anonymous_not_found = [TagState("r", t, NOT_FOUND, "x", False) for t in "abcd"]
        self.assertEqual(len(prepush_blockers(anonymous_not_found)), 4)
        self.assertTrue(prepush_blockers([TagState("r", "a", NOT_FOUND, "x", True)]))  # incomplete set


class ManifestParsingTest(unittest.TestCase):
    def test_digest_is_computed_and_header_cross_checked(self):
        body = json.dumps({"schemaVersion": 2, "mediaType": MEDIA_OCI_MANIFEST}).encode()
        digest, media_type, _ = parse_manifest_response(
            Response(200, {"content-type": MEDIA_OCI_MANIFEST, "docker-content-digest": digest_of(body)}, body), "v1")
        self.assertEqual((digest, media_type), (digest_of(body), MEDIA_OCI_MANIFEST))
        with self.assertRaisesRegex(RegistryError, "header digest"):
            parse_manifest_response(
                Response(200, {"content-type": MEDIA_OCI_MANIFEST, "docker-content-digest": "sha256:" + "0" * 64}, body), "v1")
        with self.assertRaisesRegex(RegistryError, "body digest"):
            parse_manifest_response(Response(200, {"content-type": MEDIA_OCI_MANIFEST}, body), "sha256:" + "0" * 64)

    def test_unsupported_or_inconsistent_media_type(self):
        body = json.dumps({"schemaVersion": 1}).encode()
        with self.assertRaisesRegex(RegistryError, "media type"):
            parse_manifest_response(Response(200, {"content-type": "application/json"}, body), "v1")
        body = json.dumps({"mediaType": MEDIA_OCI_MANIFEST}).encode()
        with self.assertRaisesRegex(RegistryError, "content type"):
            parse_manifest_response(Response(200, {"content-type": "application/vnd.oci.image.index.v1+json"}, body), "v1")

    def test_index_selects_single_amd64_manifest(self):
        image = FakeImage("backend", use_index=True)
        index = json.loads(image.manifests[image.top][1])
        self.assertEqual(select_platform_manifest(index), digest_of(image.manifest))
        index["manifests"] = [m for m in index["manifests"] if m["platform"]["os"] != "linux"]
        with self.assertRaises(RegistryError):
            select_platform_manifest(index)


class ResolveImagesTest(unittest.TestCase):
    def client(self, **kwargs):
        registry, images = published_registry(**kwargs)
        return RegistryClient(registry, credentials=("actor", "token")), registry, images

    def test_resolves_both_tags_and_describes_image(self):
        client, registry, images = self.client()
        resolved = resolve_release_images(client, VERSION, SHA)
        backend = resolved["backend"]
        self.assertEqual(backend["digest"], images["backend"].top)
        self.assertEqual(backend["ref"], f"ghcr.io/henric0612/rag-news-backend@{images['backend'].top}")
        self.assertEqual(backend["tags"], [VERSION, SHA_TAG])
        self.assertEqual((backend["compressed_size_bytes"], backend["max_layer_bytes"]), (6000, 5000))
        self.assertEqual(backend["platform"], "linux/amd64")
        self.assertEqual(backend["labels"]["org.opencontainers.image.revision"], SHA)
        # Blob redirects go to a storage host without the registry credentials.
        storage_calls = [c for c in registry.calls if "storage.example" in c[1]]
        self.assertTrue(storage_calls)
        self.assertTrue(all("Authorization" not in c[2] for c in storage_calls))

    def test_index_digest_is_kept_as_release_digest(self):
        client, _, images = self.client(use_index=True)
        resolved = resolve_release_images(client, VERSION, SHA)
        self.assertEqual(resolved["frontend"]["digest"], images["frontend"].top)
        self.assertEqual(resolved["frontend"]["media_type"], "application/vnd.oci.image.index.v1+json")

    def test_tags_with_different_digests_fail(self):
        client, _, _ = self.client(frontend_version_digest=True)
        with self.assertRaisesRegex(RegistryError, "different digests"):
            resolve_release_images(client, VERSION, SHA)

    def test_missing_tag_fails(self):
        client, registry, _ = self.client()
        del registry.packages[FakeRegistry.name("backend")].tags[VERSION]
        with self.assertRaises(RegistryError):
            resolve_release_images(client, VERSION, SHA)

    def test_denied_token_fails(self):
        registry, _ = published_registry(public=False)
        registry.auth_ok = False
        with self.assertRaisesRegex(RegistryError, "token denied"):
            resolve_release_images(RegistryClient(registry, credentials=("a", "b")), VERSION, SHA)


if __name__ == "__main__":
    unittest.main()
