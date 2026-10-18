import json
import re
import unittest
import urllib.parse

from deploy.rag_delivery.contract import GATE_EVIDENCE_NAME, MANIFEST_NAME, REPOSITORY, SUMS_NAME
from deploy.rag_delivery.github import GitHubClient
from deploy.rag_delivery.manifest import render_sums
from deploy.rag_delivery.registry import RegistryClient
from deploy.rag_delivery.release import (
    ReleaseError,
    anonymous_pull_errors,
    check_release_state,
    create_draft,
    cross_check_digests,
    drafts_to_delete,
    marker_run_id,
    publish,
    release_notes,
    verify_draft,
    verify_tag,
)
from deploy.rag_delivery.transport import Response
from support import (
    RELEASE_RUN_ID,
    SHA,
    TAG_OBJECT_SHA,
    VERSION,
    FakeImage,
    FakePackage,
    FakeRegistry,
    gate_evidence,
    published_registry,
    quiet,
    tag_object_doc,
    tag_ref_doc,
    valid_manifest,
)


def assets():
    manifest = (json.dumps(valid_manifest(), indent=2, sort_keys=True) + "\n").encode()
    evidence = (json.dumps(gate_evidence(), indent=2, sort_keys=True) + "\n").encode()
    files = {MANIFEST_NAME: manifest, GATE_EVIDENCE_NAME: evidence}
    files[SUMS_NAME] = render_sums(files).encode()
    return files


class FakeReleaseAPI:
    """Stateful stand-in for the GitHub releases API of one repository."""

    def __init__(self, releases=None, tag_exists=True, immutable_on_publish=True):
        self.releases = list(releases or [])
        self.tag_exists = tag_exists
        self.immutable_on_publish = immutable_on_publish
        self.next_id = 500
        self.calls = []
        self.tamper = {}

    def _json(self, status, payload):
        return Response(status, {}, json.dumps(payload).encode())

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers or {})))
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.replace(f"/repos/{REPOSITORY}/", "", 1)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        if parsed.netloc == "storage.example":
            if "Authorization" in headers:
                return Response(400, {}, b"credentials forwarded")
            asset_id = int(path.strip("/"))
            return Response(200, {}, self._asset(asset_id)["data"])
        if parsed.netloc == "uploads.github.com":
            release = self._release(int(re.search(r"releases/(\d+)/assets", path).group(1)))
            asset = {"id": self.next_id, "name": query["name"], "state": "uploaded",
                     "data": self.tamper.get(query["name"], body)}
            self.next_id += 1
            release["assets"].append(asset)
            return self._json(201, self._public(asset))
        if method == "GET" and path == f"git/ref/tags/{VERSION}":
            return self._json(200, tag_ref_doc()) if self.tag_exists else self._json(404, {})
        if method == "GET" and path == f"git/tags/{TAG_OBJECT_SHA}":
            return self._json(200, tag_object_doc())
        if method == "GET" and path == f"releases/tags/{VERSION}":
            published = [r for r in self.releases if r["tag_name"] == VERSION and not r["draft"]]
            return self._json(200, self._public(published[0])) if published else self._json(404, {})
        if method == "GET" and path == "releases":
            page = int(query.get("page", "1"))
            return self._json(200, [self._public(r) for r in self.releases] if page == 1 else [])
        match = re.fullmatch(r"releases/(\d+)", path)
        if match:
            release = self._release(int(match.group(1)))
            if method == "GET":
                return self._json(200, self._public(release))
            if method == "DELETE":
                self.releases.remove(release)
                return Response(204, {}, b"")
            if method == "PATCH":
                if json.loads(body).get("draft") is False:
                    release["draft"] = False
                    release["immutable"] = self.immutable_on_publish
                return self._json(200, self._public(release))
        if method == "POST" and path == "releases":
            payload = json.loads(body)
            release = {"id": self.next_id, "tag_name": payload["tag_name"], "body": payload["body"],
                       "draft": payload["draft"], "immutable": False, "assets": [],
                       "upload_url": f"https://uploads.github.com/repos/{REPOSITORY}/releases/{self.next_id}/assets{{?name,label}}"}
            self.next_id += 1
            self.releases.append(release)
            return self._json(201, self._public(release))
        match = re.fullmatch(r"releases/assets/(\d+)", path)
        if match and method == "GET":
            assert headers.get("Accept") == "application/octet-stream"
            return Response(302, {"location": f"https://storage.example/{match.group(1)}"}, b"")
        return self._json(404, {"message": "Not Found"})

    def _release(self, release_id):
        return next(r for r in self.releases if r["id"] == release_id)

    def _asset(self, asset_id):
        return next(a for r in self.releases for a in r["assets"] if a["id"] == asset_id)

    @staticmethod
    def _public(item):
        result = {k: v for k, v in item.items() if k != "data"}
        if "assets" in result:
            result["assets"] = [{k: v for k, v in a.items() if k != "data"} for a in result["assets"]]
        return result

    def methods(self):
        return [(m, urllib.parse.urlsplit(u).path) for m, u, _ in self.calls]


def draft(release_id, run_id=RELEASE_RUN_ID, tag=VERSION, is_draft=True, body=None):
    body = body if body is not None else f"x\n<!-- rag-delivery:release-run-id={run_id} -->\n"
    return {"id": release_id, "tag_name": tag, "draft": is_draft, "body": body, "assets": [], "immutable": False}


def client(api):
    return GitHubClient("token", REPOSITORY, api)


class DraftDecisionTest(unittest.TestCase):
    def test_no_release(self):
        self.assertEqual(drafts_to_delete([draft(1, tag="v0.0.9")], VERSION, RELEASE_RUN_ID), [])

    def test_same_run_draft_is_deleted(self):
        self.assertEqual(drafts_to_delete([draft(7)], VERSION, RELEASE_RUN_ID), [7])

    def test_published_release_fails(self):
        with self.assertRaisesRegex(ReleaseError, "not a draft"):
            drafts_to_delete([draft(7, is_draft=False)], VERSION, RELEASE_RUN_ID)

    def test_foreign_or_unmarked_draft_fails(self):
        for release in (draft(7, run_id=123), draft(7, body="manual draft"), draft(7, body=None) | {"body": None}):
            with self.subTest(body=release["body"]):
                with self.assertRaisesRegex(ReleaseError, "not created by run"):
                    drafts_to_delete([release], VERSION, RELEASE_RUN_ID)

    def test_notes_carry_marker(self):
        notes = release_notes(valid_manifest(), RELEASE_RUN_ID)
        self.assertEqual(marker_run_id(notes), str(RELEASE_RUN_ID))
        self.assertIn("ghcr.io/henric0612/rag-news-backend@sha256:", notes)
        self.assertIsNone(marker_run_id("no marker"))


class ReleaseStateTest(unittest.TestCase):
    def test_published_release_rejected_without_changes(self):
        api = FakeReleaseAPI([draft(7, is_draft=False)])
        with self.assertRaisesRegex(ReleaseError, "already exists"):
            check_release_state(client(api), VERSION, RELEASE_RUN_ID)
        self.assertFalse([c for c in api.methods() if c[0] != "GET"])

    def test_same_run_draft_deleted(self):
        api = FakeReleaseAPI([draft(7)])
        quiet(check_release_state, client(api), VERSION, RELEASE_RUN_ID)
        self.assertEqual(api.releases, [])

    def test_foreign_draft_not_deleted(self):
        api = FakeReleaseAPI([draft(7, run_id=99)])
        with self.assertRaises(ReleaseError):
            check_release_state(client(api), VERSION, RELEASE_RUN_ID)
        self.assertEqual(len(api.releases), 1)
        self.assertNotIn("DELETE", [m for m, _ in api.methods()])


class PublishFlowTest(unittest.TestCase):
    def run_flow(self, api):
        github = client(api)
        files = assets()
        manifest = json.loads(files[MANIFEST_NAME])
        quiet(check_release_state, github, VERSION, RELEASE_RUN_ID)
        release_id = quiet(create_draft, github, manifest, RELEASE_RUN_ID, files)
        quiet(verify_draft, github, release_id, VERSION, files)
        quiet(publish, github, release_id, VERSION, SHA, TAG_OBJECT_SHA)
        return release_id

    def test_draft_verify_publish_readback(self):
        api = FakeReleaseAPI()
        release_id = self.run_flow(api)
        release = api.releases[0]
        self.assertEqual((release["id"], release["draft"], release["immutable"]), (release_id, False, True))
        self.assertEqual(sorted(a["name"] for a in release["assets"]), sorted([MANIFEST_NAME, GATE_EVIDENCE_NAME, SUMS_NAME]))
        storage = [c for c in api.calls if "storage.example" in c[1]]
        self.assertEqual(len(storage), 3)
        self.assertTrue(all("Authorization" not in c[2] for c in storage))
        # Draft is created before publication; publication happens exactly once.
        writes = [m for m, p in api.methods() if m in ("POST", "PATCH")]
        self.assertEqual(writes[0], "POST")
        self.assertEqual(writes.count("PATCH"), 1)

    def test_rerun_after_failed_attempt_replaces_same_run_draft(self):
        api = FakeReleaseAPI([draft(7)])
        self.run_flow(api)
        self.assertEqual(len(api.releases), 1)
        self.assertNotEqual(api.releases[0]["id"], 7)

    def test_missing_tag_creates_nothing(self):
        api = FakeReleaseAPI(tag_exists=False)
        with self.assertRaisesRegex(ReleaseError, "must exist"):
            create_draft(client(api), valid_manifest(), RELEASE_RUN_ID, assets())
        self.assertEqual(api.releases, [])

    def test_tampered_upload_is_not_published(self):
        api = FakeReleaseAPI()
        api.tamper[MANIFEST_NAME] = b"{}"
        github = client(api)
        files = assets()
        release_id = quiet(create_draft, github, json.loads(files[MANIFEST_NAME]), RELEASE_RUN_ID, files)
        with self.assertRaisesRegex(ReleaseError, "differ"):
            verify_draft(github, release_id, VERSION, files)
        self.assertTrue(api.releases[0]["draft"])

    def test_missing_asset_is_not_published(self):
        api = FakeReleaseAPI()
        github = client(api)
        files = assets()
        release_id = quiet(create_draft, github, json.loads(files[MANIFEST_NAME]), RELEASE_RUN_ID, files)
        api.releases[0]["assets"].pop()
        with self.assertRaisesRegex(ReleaseError, "release assets"):
            verify_draft(github, release_id, VERSION, files)

    def test_not_immutable_after_publish_is_reported_incomplete(self):
        api = FakeReleaseAPI(immutable_on_publish=False)
        with self.assertRaisesRegex(ReleaseError, "INCOMPLETE"):
            self.run_flow(api)


class TagAndDigestTest(unittest.TestCase):
    def test_tag_must_still_peel_to_gated_commit(self):
        api = FakeReleaseAPI()
        verify_tag(client(api), VERSION, SHA, TAG_OBJECT_SHA)
        with self.assertRaises(ReleaseError):
            verify_tag(client(api), VERSION, "f" * 40, TAG_OBJECT_SHA)
        with self.assertRaises(ReleaseError):
            verify_tag(client(FakeReleaseAPI(tag_exists=False)), VERSION, SHA, TAG_OBJECT_SHA)

    def test_upstream_digest_cross_check(self):
        images = {"backend": {"digest": "sha256:" + "a" * 64}, "frontend": {"digest": "sha256:" + "b" * 64}}
        quiet(cross_check_digests, images, {"backend": "", "frontend": ""})
        quiet(cross_check_digests, images, {"backend": "sha256:" + "a" * 64, "frontend": None})
        with self.assertRaisesRegex(ReleaseError, "build-push output"):
            cross_check_digests(images, {"backend": "sha256:" + "c" * 64, "frontend": ""})


class AnonymousPullTest(unittest.TestCase):
    def manifest_for(self, registry):
        manifest = valid_manifest()
        for service in ("backend", "frontend"):
            top = registry.packages[FakeRegistry.name(service)].tags[VERSION]
            manifest["images"][service]["digest"] = top
            manifest["images"][service]["ref"] = f"{manifest['images'][service]['repository']}@{top}"
        return manifest

    def test_private_packages_fail_closed(self):
        registry, _ = published_registry(public=False)
        errors = anonymous_pull_errors(RegistryClient(registry), self.manifest_for(registry))
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("not public" in e for e in errors))

    def test_public_packages_pass(self):
        registry, _ = published_registry(public=True)
        self.assertEqual(anonymous_pull_errors(RegistryClient(registry), self.manifest_for(registry)), [])

    def test_label_mismatch_fails(self):
        registry, _ = published_registry(public=True)
        package = registry.packages[FakeRegistry.name("frontend")]
        wrong = FakeImage("frontend", app_version="0.0.0-dev")
        package.put(wrong, [VERSION, "sha-6e5af4a"])
        errors = anonymous_pull_errors(RegistryClient(registry), self.manifest_for(registry))
        self.assertTrue(any("org.opencontainers.image.version" in e for e in errors))

    def test_missing_digest_fails(self):
        registry, _ = published_registry(public=True)
        manifest = self.manifest_for(registry)
        manifest["images"]["backend"]["digest"] = "sha256:" + "0" * 64
        errors = anonymous_pull_errors(RegistryClient(registry), manifest)
        self.assertTrue(any("anonymous pull failed" in e for e in errors))

    def test_one_public_one_private_fails(self):
        registry, _ = published_registry(public=True)
        registry.packages[FakeRegistry.name("frontend")].public = False
        errors = anonymous_pull_errors(RegistryClient(registry), self.manifest_for(registry))
        self.assertEqual(len(errors), 1)
        self.assertIn("rag-news-frontend", errors[0])


if __name__ == "__main__":
    unittest.main()
