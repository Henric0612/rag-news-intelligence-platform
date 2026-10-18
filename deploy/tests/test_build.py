import json
import tempfile
import unittest
from pathlib import Path

from deploy.rag_delivery import declared_schema
from deploy.rag_delivery.build import (
    BuildError,
    build_release_images,
    content_violations,
    image_identity_errors,
    parse_models,
    push_release_images,
    repo_digest,
)
from deploy.rag_delivery.contract import INPUT_FILES, ContractError
from deploy.rag_delivery.registry import RegistryClient
from support import (
    APP_VERSION,
    SHA,
    SHA_TAG,
    VERSION,
    FakeImage,
    FakePackage,
    FakeRegistry,
    quiet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = """\
ARG EMBEDDING_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
ARG RERANK_REVISION=233902d25c440f23af6f7d6e94d2946bac0bee0a
RUN python -c "e = snapshot_download('sentence-transformers/all-MiniLM-L6-v2', revision='${EMBEDDING_REVISION}', cache_dir='/x'); r = snapshot_download('cross-encoder/ms-marco-MiniLM-L-6-v2', revision='${RERANK_REVISION}', cache_dir='/x')"
"""


class ContentCheckTest(unittest.TestCase):
    def test_clean_filesystem(self):
        names = ["app/", "app/Backend/app.py", "app/Backend/env.example", "app/Backend/data/uploads/",
                 "app/Backend/data/uploads", "app/Backend/data/sqlite/", "srv/index.html",
                 "lib/apk/db/installed", "opt/huggingface/hub/model.safetensors.index.json", "./"]
        self.assertEqual(content_violations(names), [])

    def test_forbidden_names(self):
        forbidden = ["app/Backend/.env", "app/.env.production", "srv/.env.local", "app/Backend/data/sqlite/knowledge.db",
                     "tmp/cache.sqlite", "tmp/cache.sqlite3", "x/data.sqlite-journal",
                     "app/Backend/data/faiss/knowledge.index", "app/Backend/data/faiss/id_mapping.json",
                     "./app/Backend/.env"]
        for name in forbidden:
            with self.subTest(name=name):
                self.assertEqual(len(content_violations([name])), 1)

    def test_uploads_must_be_empty(self):
        for name in ["app/Backend/data/uploads/report.pdf", "app/Backend/data/uploads/sub/", "srv/uploads/a.png"]:
            with self.subTest(name=name):
                self.assertTrue(any("uploads" in v for v in content_violations([name])))


class ModelsAndInputsTest(unittest.TestCase):
    def test_parse_models_fixture(self):
        models = parse_models(DOCKERFILE)
        self.assertEqual(models["embedding"], {"id": "sentence-transformers/all-MiniLM-L6-v2",
                                               "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"})
        self.assertEqual(models["reranker"]["id"], "cross-encoder/ms-marco-MiniLM-L-6-v2")

    def test_parse_models_from_repository_dockerfile(self):
        models = parse_models((REPO_ROOT / "Backend/Dockerfile").read_text())
        self.assertEqual(set(models), {"embedding", "reranker"})

    def test_unpinned_or_missing_models_rejected(self):
        with self.assertRaises(BuildError):
            parse_models(DOCKERFILE.replace("1110a243fdf4706b3f48f1d95db1a4f5529b4d41", "main"))
        with self.assertRaises(BuildError):
            parse_models(DOCKERFILE.split("RUN")[0])
        with self.assertRaises(BuildError):
            parse_models(DOCKERFILE.replace("RERANK_REVISION}", "OTHER_REVISION}"))

    def test_input_files_exist_in_repository(self):
        for path in INPUT_FILES:
            self.assertTrue((REPO_ROOT / path).is_file(), path)

    def test_repo_digest(self):
        digest = "sha256:" + "a" * 64
        self.assertEqual(repo_digest("python:3.13-slim", [f"python@{digest}"]), digest)
        for digests in ([], None, [f"node@{digest}"], [f"python@{digest}", f"python@sha256:{'b' * 64}"]):
            with self.subTest(digests=digests):
                with self.assertRaises(BuildError):
                    repo_digest("python:3.13-slim", digests)


def inspect_doc(service, version=APP_VERSION, sha=SHA, arch="amd64", env=None):
    labels = {
        "org.opencontainers.image.source": "https://github.com/Henric0612/rag-news-intelligence-platform",
        "org.opencontainers.image.version": version,
        "org.opencontainers.image.revision": sha,
        "org.opencontainers.image.title": f"rag-news-{service}",
        "org.opencontainers.image.licenses": "Apache-2.0",  # inherited from caddy; not asserted here
    }
    if env is None:
        env = [f"APP_VERSION={version}", f"GIT_SHA={sha}"] if service == "backend" else []
    return {"Id": f"sha256:{service[0] * 64}", "Size": 123456, "Os": "linux", "Architecture": arch,
            "Config": {"Labels": labels, "Env": env}}


class IdentityReadbackTest(unittest.TestCase):
    def test_matching_identity(self):
        for service in ("backend", "frontend"):
            self.assertEqual(image_identity_errors(service, inspect_doc(service), APP_VERSION, SHA), [])

    def test_default_build_identity_rejected(self):
        errors = image_identity_errors("frontend", inspect_doc("frontend", "0.0.0-dev", "unknown"), APP_VERSION, SHA)
        self.assertEqual(len(errors), 2)

    def test_backend_env_and_platform(self):
        self.assertTrue(image_identity_errors("backend", inspect_doc("backend", env=[]), APP_VERSION, SHA))
        self.assertTrue(image_identity_errors("backend", inspect_doc("backend", arch="arm64"), APP_VERSION, SHA))


class FakeDocker:
    def __init__(self, inspects=None, schema_output=None):
        self.commands = []
        self.inspects = inspects or {s: inspect_doc(s) for s in ("backend", "frontend")}
        self.schema_output = schema_output or json.dumps(
            {"declared_schema_fingerprint": "sha256:" + "5" * 64, "tables": ["users"]})

    def __call__(self, args, stdin_text=None):
        self.commands.append(args)
        if args[:2] == ["docker", "image"] and "{{json .RepoDigests}}" in args:
            name = args[-1].rsplit(":", 1)[0]
            return json.dumps([f"{name}@sha256:{'9' * 64}"])
        if args[:3] == ["docker", "image", "inspect"]:
            return json.dumps([self.inspects["backend" if "backend" in args[-1] else "frontend"]])
        if args[:2] == ["docker", "run"]:
            assert "--network" in args and "none" in args
            assert "declared_schema_fingerprint" in stdin_text
            return "some log line\n" + self.schema_output + "\n"
        if args[:2] == ["docker", "version"]:
            return "29.1.0\n"
        return ""


def source_tree():
    directory = tempfile.TemporaryDirectory()
    root = Path(directory.name)
    for path in INPUT_FILES:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(DOCKERFILE if path == "Backend/Dockerfile" else f"content of {path}\n")
    return directory


CONTEXT = {"release_run_id": 1, "run_attempt": 1, "runner": "Linux/X64",
           "workflow_ref": "Henric0612/rag-news-intelligence-platform/.github/workflows/release.yml@refs/tags/v0.1.0",
           "now": lambda: "2026-10-19T08:10:00Z"}


class BuildReleaseImagesTest(unittest.TestCase):
    def build(self, docker, names=("app/Backend/app.py",)):
        with source_tree() as root:
            return quiet(build_release_images, root, VERSION, SHA, CONTEXT, run=docker,
                         list_names=lambda image: list(names))

    def test_builds_with_identity_and_records_evidence(self):
        docker = FakeDocker()
        evidence = self.build(docker)
        builds = [c for c in docker.commands if c[:2] == ["docker", "build"]]
        self.assertEqual(len(builds), 2)
        for command in builds:
            for flag in ("--pull", "--platform", "linux/amd64", f"APP_VERSION={APP_VERSION}", f"GIT_SHA={SHA}"):
                self.assertIn(flag, command)
        self.assertIn(f"ghcr.io/henric0612/rag-news-backend:{SHA_TAG}", builds[0])
        self.assertIn(f"ghcr.io/henric0612/rag-news-backend:{VERSION}", builds[0])
        self.assertFalse([c for c in docker.commands if c[:2] in (["docker", "push"], ["docker", "login"])])
        self.assertEqual(evidence["data_compat"]["declared_schema_fingerprint"], "sha256:" + "5" * 64)
        self.assertEqual(evidence["data_compat"]["embedding"]["id"], "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(set(evidence["inputs"]["base_images"]), {"python:3.13-slim", "node:24-alpine", "caddy:2-alpine"})
        self.assertEqual(len(evidence["inputs"]["files"]), 5)
        self.assertEqual(evidence["images"]["frontend"]["content_check"]["violations"], [])
        self.assertEqual(evidence["build"]["docker_version"], "29.1.0")

    def test_forbidden_content_fails(self):
        with self.assertRaisesRegex(BuildError, "forbidden name"):
            self.build(FakeDocker(), names=("app/Backend/.env",))
        with self.assertRaisesRegex(BuildError, "uploads"):
            self.build(FakeDocker(), names=("app/Backend/data/uploads/x.pdf",))

    def test_empty_listing_fails(self):
        with self.assertRaisesRegex(BuildError, "empty"):
            self.build(FakeDocker(), names=())

    def test_label_mismatch_fails(self):
        docker = FakeDocker(inspects={"backend": inspect_doc("backend"),
                                      "frontend": inspect_doc("frontend", version="0.0.0-dev")})
        with self.assertRaisesRegex(BuildError, "org.opencontainers.image.version"):
            self.build(docker)

    def test_invalid_schema_output_fails(self):
        with self.assertRaisesRegex(BuildError, "declared schema"):
            self.build(FakeDocker(schema_output='{"declared_schema_fingerprint": "abc", "tables": []}'))

    def test_invalid_identity_inputs_fail_before_docker(self):
        docker = FakeDocker()
        with self.assertRaises(ContractError):
            self.build_with(docker, "0.1.0", SHA)
        with self.assertRaises(ContractError):
            self.build_with(docker, VERSION, SHA[:7])
        self.assertEqual(docker.commands, [])

    def build_with(self, docker, version, sha):
        with source_tree() as root:
            return build_release_images(root, version, sha, CONTEXT, run=docker, list_names=lambda i: ["a"])


class PushDocker:
    """Fake docker for pushes: a push publishes the local image to the fake registry."""

    def __init__(self, registry, local_digest_override=None):
        self.registry = registry
        self.local_digest_override = local_digest_override
        self.commands = []
        self.images = {s: FakeImage(s) for s in ("backend", "frontend")}

    def __call__(self, args, stdin_text=None):
        self.commands.append(args)
        if args[:2] == ["docker", "push"]:
            repository, tag = args[2].rsplit(":", 1)
            service = "backend" if "backend" in repository else "frontend"
            name = repository.split("/", 1)[1]
            package = self.registry.packages.setdefault(name, FakePackage(public=False))
            package.put(self.images[service], [tag])
            return ""
        if args[:3] == ["docker", "image", "inspect"]:
            repository = args[-1].rsplit(":", 1)[0]
            service = "backend" if "backend" in repository else "frontend"
            digest = self.local_digest_override or self.images[service].top
            return json.dumps([f"{repository}@{digest}"])
        raise AssertionError(f"unexpected command {args}")

    def pushes(self):
        return [c[2] for c in self.commands if c[:2] == ["docker", "push"]]


class PushZeroWriteTest(unittest.TestCase):
    def push(self, registry, credentials=("actor", "token"), **kwargs):
        docker = PushDocker(registry, **kwargs)
        client = RegistryClient(registry, credentials=credentials)
        try:
            return docker, quiet(push_release_images, client, VERSION, SHA, run=docker,
                                 sleep=lambda seconds: None), None
        except BuildError as error:
            return docker, None, error

    def test_confirmed_absence_pushes_in_frozen_order_and_reads_back(self):
        docker, result, error = self.push(FakeRegistry({}))
        self.assertIsNone(error)
        self.assertEqual(docker.pushes(), [
            f"ghcr.io/henric0612/rag-news-backend:{SHA_TAG}",
            f"ghcr.io/henric0612/rag-news-frontend:{SHA_TAG}",
            f"ghcr.io/henric0612/rag-news-backend:{VERSION}",
            f"ghcr.io/henric0612/rag-news-frontend:{VERSION}",
        ])
        self.assertEqual(result["images"]["backend"]["digest"], docker.images["backend"].top)
        self.assertEqual({s["state"] for s in result["prepush"]}, {"NOT_FOUND"})

    def test_denied_authenticated_lookup_pushes_nothing(self):
        docker, _, error = self.push(FakeRegistry({}, auth_ok=False))
        self.assertIn("refusing to push", str(error))
        self.assertEqual(docker.pushes(), [])

    def test_one_denied_repository_pushes_nothing(self):
        registry = FakeRegistry({}, auth_denied_repos={FakeRegistry.name("frontend")})
        docker, _, error = self.push(registry)
        self.assertIn("UNKNOWN", str(error))
        self.assertEqual(docker.pushes(), [])

    def test_existing_tag_pushes_nothing(self):
        for tag in (SHA_TAG, VERSION):
            with self.subTest(tag=tag):
                package = FakePackage(public=False)
                package.put(FakeImage("frontend", app_version="0.0.9"), [tag])
                docker, _, error = self.push(FakeRegistry({FakeRegistry.name("frontend"): package}))
                self.assertIn("EXISTS", str(error))
                self.assertEqual(docker.pushes(), [])

    def test_network_failure_pushes_nothing(self):
        docker, _, error = self.push(FakeRegistry({}, fail_urls=("https://ghcr.io/v2/",)))
        self.assertIn("UNKNOWN", str(error))
        self.assertEqual(docker.pushes(), [])

    def test_anonymous_not_found_is_not_enough(self):
        packages = {FakeRegistry.name(s): FakePackage(public=True) for s in ("backend", "frontend")}
        for service, package in zip(("backend", "frontend"), packages.values()):
            package.put(FakeImage(service, app_version="0.0.9"), ["v0.0.9"])
        docker, _, error = self.push(FakeRegistry(packages), credentials=None)
        self.assertIn("refusing to push", str(error))
        self.assertEqual(docker.pushes(), [])

    def test_transient_readback_failure_is_retried(self):
        registry = FakeRegistry({})
        failures = {"left": 2}
        original = registry.__call__

        def flaky(method, url, headers, body):
            pushed = len(registry.packages) == 2 and all(len(p.tags) == 2 for p in registry.packages.values())
            if pushed and "/manifests/" in url and failures["left"]:
                failures["left"] -= 1
                from deploy.rag_delivery.transport import TransportError
                raise TransportError("simulated transient failure")
            return original(method, url, headers, body)

        docker = PushDocker(registry)
        client = RegistryClient(flaky, credentials=("actor", "token"))
        result = quiet(push_release_images, client, VERSION, SHA, run=docker, sleep=lambda seconds: None)
        self.assertEqual(len(docker.pushes()), 4)
        self.assertEqual(result["images"]["backend"]["digest"], docker.images["backend"].top)

    def test_persistent_readback_failure_fails_without_repush(self):
        registry = FakeRegistry({})
        original = registry.__call__

        def broken(method, url, headers, body):
            pushed = len(registry.packages) == 2 and all(len(p.tags) == 2 for p in registry.packages.values())
            if pushed and "/manifests/" in url:
                from deploy.rag_delivery.transport import TransportError
                raise TransportError("registry unavailable")
            return original(method, url, headers, body)

        docker = PushDocker(registry)
        with self.assertRaisesRegex(BuildError, "after 3 attempts"):
            quiet(push_release_images, RegistryClient(broken, credentials=("a", "b")), VERSION, SHA,
                  run=docker, sleep=lambda seconds: None)
        self.assertEqual(len(docker.pushes()), 4)

    def test_readback_mismatch_with_local_image_fails(self):
        docker, _, error = self.push(FakeRegistry({}), local_digest_override="sha256:" + "0" * 64)
        self.assertIn("not in local RepoDigests", str(error))


class DeclaredSchemaTest(unittest.TestCase):
    def test_fingerprint_is_order_independent_and_sensitive(self):
        first = {"users": ["CREATE TABLE users (id INTEGER)\n"], "items": ["CREATE TABLE items (id INTEGER)"]}
        second = {"items": ["  CREATE TABLE items (id INTEGER)"], "users": ["CREATE TABLE users (id INTEGER)"]}
        self.assertEqual(declared_schema.fingerprint(first), declared_schema.fingerprint(second))
        self.assertRegex(declared_schema.fingerprint(first), r"^sha256:[0-9a-f]{64}$")
        changed = {"users": ["CREATE TABLE users (id INTEGER, name TEXT)"], "items": first["items"]}
        self.assertNotEqual(declared_schema.fingerprint(first), declared_schema.fingerprint(changed))
        with_index = {"users": first["users"] + ["CREATE INDEX ix_users_id ON users (id)"], "items": first["items"]}
        self.assertNotEqual(declared_schema.fingerprint(first), declared_schema.fingerprint(with_index))

    def test_script_imports_only_stdlib_at_module_level(self):
        source = (REPO_ROOT / "deploy/rag_delivery/declared_schema.py").read_text()
        top_level_imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
        self.assertEqual(top_level_imports, ["import hashlib", "import json"])


if __name__ == "__main__":
    unittest.main()
