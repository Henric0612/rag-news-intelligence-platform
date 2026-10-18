import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deploy.rag_delivery import compose_check
from deploy.rag_delivery.compose_check import (
    CHECK_PROJECT,
    CHECK_PROJECTS,
    COMPOSE_FILE,
    RELEASE_OVERRIDE,
    ComposeCheckError,
    check_release_compose,
    fake_image_refs,
    release_config_errors,
    require_project,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES = fake_image_refs()

# The frozen CD-WP4 override, byte for byte.
FROZEN_OVERRIDE = """\
services:
  backend:
    build: !reset null
    image: ${RAG_BACKEND_IMAGE:?set backend image digest ref}
    pull_policy: never
  frontend:
    build: !reset null
    image: ${RAG_FRONTEND_IMAGE:?set frontend image digest ref}
    pull_policy: never
"""


# Shapes follow `docker compose config --format json` (Compose v5) for compose.yaml.
def base_config(project=CHECK_PROJECT):
    return {
        "name": project,
        "networks": {"app_network": {"name": f"{project}_app_network", "driver": "bridge", "ipam": {}}},
        "services": {
            "backend": {
                "build": {"context": "/repo/Backend", "dockerfile": "Dockerfile"},
                "command": None,
                "entrypoint": None,
                "environment": {
                    "CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
                    "FLASK_ENV": "production",
                    "FRONTEND_URL": "http://localhost:3000",
                    "JWT_SECRET_KEY": "rag-cd-compose-check-jwt-key",
                    "LLM_MODEL": "qwen3:8b",
                    "OLLAMA_HOST": "http://host.docker.internal:11434",
                    "RAG_DATA_DIR": "/app/Backend/data",
                    "SECRET_KEY": "rag-cd-compose-check-secret-key",
                },
                "networks": {"app_network": None},
                "volumes": [{"type": "volume", "source": "rag_data", "target": "/app/Backend/data",
                             "volume": {}}],
                "healthcheck": {"test": ["CMD", "python", "-c", "import urllib.request"],
                                "timeout": "5s", "interval": "10s", "retries": 6, "start_period": "30s"},
                "ports": [{"mode": "ingress", "host_ip": "127.0.0.1", "target": 5000,
                           "published": "5000", "protocol": "tcp"}],
            },
            "frontend": {
                "build": {"context": "/repo/Frontend", "dockerfile": "Dockerfile"},
                "command": None,
                "entrypoint": None,
                "networks": {"app_network": None},
                "healthcheck": {"test": ["CMD", "wget", "--quiet", "--spider", "http://127.0.0.1:3000/"],
                                "timeout": "5s", "interval": "10s", "retries": 3, "start_period": "10s"},
                "ports": [{"mode": "ingress", "host_ip": "127.0.0.1", "target": 3000,
                           "published": "3000", "protocol": "tcp"}],
            },
        },
        "volumes": {"rag_data": {"name": f"{project}_rag_data"}},
    }


def merged_config(project=CHECK_PROJECT):
    config = base_config(project)
    for service, value in config["services"].items():
        del value["build"]
        value["image"] = fake_image_refs(project)[service]
        value["pull_policy"] = "never"
    return config


class FakeCompose:
    """Stands in for the docker CLI: answers `config` for base and merged file sets.

    Without fixed documents it answers what Compose would for the ``-p``
    project; ``mutate(doc, project)`` then alters the merged answer.
    """

    def __init__(self, base=None, merged=None, mutate=None):
        self.base, self.merged, self.mutate = base, merged, mutate
        self.calls = []

    def __call__(self, command, cwd, env):
        env_file = command[command.index("--env-file") + 1]
        project = command[command.index("-p") + 1]
        self.calls.append({"command": command, "cwd": cwd, "env": env, "project": project,
                           "env_file": Path(env_file).read_text()})
        if RELEASE_OVERRIDE in command:
            doc = merged_config(project) if self.merged is None else self.merged
            if self.mutate:
                self.mutate(doc, project)
        else:
            doc = base_config(project) if self.base is None else self.base
        return 0, doc if isinstance(doc, str) else json.dumps(doc), ""


def errors_for(merged=None, base=None, project=CHECK_PROJECT):
    return release_config_errors(merged or merged_config(project), base or base_config(project),
                                 project, IMAGES)


def assert_error(test, merged, fragment, base=None):
    errors = errors_for(merged, base)
    test.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")


class OverrideFileTest(unittest.TestCase):
    def test_override_is_the_frozen_content(self):
        self.assertEqual((REPO_ROOT / RELEASE_OVERRIDE).read_text(), FROZEN_OVERRIDE)


class ReleaseConfigTest(unittest.TestCase):
    def test_valid_configuration_has_no_errors(self):
        self.assertEqual(errors_for(), [])

    def test_build_not_removed(self):
        for service in ("backend", "frontend"):
            merged = merged_config()
            merged["services"][service]["build"] = {"context": "/repo/x"}
            assert_error(self, merged, f"{service}: build is still configured")
            merged["services"][service]["build"] = None
            assert_error(self, merged, f"{service}: build is still configured")

    def test_image_must_be_the_exact_digest_reference(self):
        cases = {
            "ghcr.io/henric0612/rag-news-backend:v0.1.0": "not a repository@sha256",
            "ghcr.io/henric0612/rag-news-backend": "not a repository@sha256",
            "ghcr.io/henric0612/rag-news-backend:v0.1.0@sha256:" + "a" * 64: "expected",
            "ghcr.io/henric0612/rag-news-backend@sha256:" + "b" * 64: "expected",
            "ghcr.io/henric0612/rag-news-backend@sha256:" + "c" * 63: "not a repository@sha256",
            IMAGES["frontend"]: "expected",
        }
        for image, fragment in cases.items():
            with self.subTest(image=image):
                merged = merged_config()
                merged["services"]["backend"]["image"] = image
                assert_error(self, merged, f"backend: image {image!r}")
                assert_error(self, merged, fragment)
        merged = merged_config()
        del merged["services"]["frontend"]["image"]
        assert_error(self, merged, "frontend: image None")

    def test_pull_policy_must_be_never(self):
        for value in ("always", "missing", "if_not_present", "build", None):
            with self.subTest(value=value):
                merged = merged_config()
                merged["services"]["frontend"]["pull_policy"] = value
                assert_error(self, merged, "frontend: pull_policy")
        merged = merged_config()
        del merged["services"]["backend"]["pull_policy"]
        assert_error(self, merged, "backend: pull_policy None")

    def test_ports_must_bind_loopback(self):
        for host_ip in ("0.0.0.0", "", "::", None):
            with self.subTest(host_ip=host_ip):
                merged = merged_config()
                merged["services"]["backend"]["ports"][0]["host_ip"] = host_ip
                assert_error(self, merged, "is not bound to 127.0.0.1")
        merged = merged_config()
        del merged["services"]["frontend"]["ports"][0]["host_ip"]
        assert_error(self, merged, "frontend: port")
        merged = merged_config()
        merged["services"]["frontend"]["ports"].append(
            {"mode": "ingress", "host_ip": "0.0.0.0", "target": 3000, "published": "8080", "protocol": "tcp"})
        assert_error(self, merged, "is not bound to 127.0.0.1")
        merged = merged_config()
        merged["services"]["backend"]["ports"] = []
        assert_error(self, merged, "backend: no published ports")

    def test_loopback_drift_in_compose_yaml_is_caught_too(self):
        merged, base = merged_config(), base_config()
        for doc in (merged, base):
            doc["services"]["backend"]["ports"][0]["host_ip"] = "0.0.0.0"
        assert_error(self, merged, "is not bound to 127.0.0.1", base)

    def test_data_volume_source_and_target(self):
        merged = merged_config()
        merged["services"]["backend"]["volumes"][0]["source"] = "other_data"
        assert_error(self, merged, "expected named volume 'rag_data'")
        merged = merged_config()
        merged["services"]["backend"]["volumes"][0].update(type="bind", source="/srv/rag")
        assert_error(self, merged, "is a 'bind' mount")
        merged = merged_config()
        merged["services"]["backend"]["volumes"] = []
        assert_error(self, merged, "expected one mount at /app/Backend/data, found 0")
        merged = merged_config()
        merged["services"]["backend"]["volumes"].append(dict(merged["services"]["backend"]["volumes"][0]))
        assert_error(self, merged, "found 2")
        merged = merged_config()
        merged["services"]["frontend"]["volumes"] = [
            {"type": "volume", "source": "rag_data", "target": "/data", "volume": {}}]
        assert_error(self, merged, "frontend: mounts rag_data")

    def test_final_volume_name_is_project_scoped(self):
        merged = merged_config()
        merged["volumes"]["rag_data"]["name"] = "rag-news-intelligence-platform_rag_data"
        assert_error(self, merged, "expected 'rag-cd-compose-check_rag_data'")
        merged = merged_config()
        merged["volumes"]["rag_data"]["external"] = True
        assert_error(self, merged, "is external")
        merged = merged_config()
        del merged["volumes"]
        assert_error(self, merged, "top-level volume rag_data is not declared")

    def test_logical_source_is_not_confused_with_the_final_name(self):
        # A mount whose source already is the final name would bypass the
        # top-level volume mapping; only the logical key is accepted.
        merged = merged_config()
        merged["services"]["backend"]["volumes"][0]["source"] = "rag-cd-compose-check_rag_data"
        assert_error(self, merged, "expected named volume 'rag_data'")

    def test_project_isolation(self):
        merged = merged_config()
        merged["name"] = "rag-news-intelligence-platform"
        assert_error(self, merged, "merged project name")
        merged = merged_config()
        merged["networks"]["app_network"]["name"] = "rag-news-intelligence-platform_app_network"
        assert_error(self, merged, "network app_network is not project-scoped")
        for project in ("rag-news-intelligence-platform", "rag-cd-", "RAG-CD-x", "x-rag-cd-y", "", None):
            with self.subTest(project=project):
                with self.assertRaises(ComposeCheckError):
                    require_project(project)
        self.assertEqual(require_project("rag-cd-accept"), "rag-cd-accept")

    def test_service_missing_or_extra(self):
        for service in ("backend", "frontend"):
            with self.subTest(service=service):
                merged = merged_config()
                del merged["services"][service]
                assert_error(self, merged, f"{service}: missing from the merged configuration")
                base = base_config()
                del base["services"][service]
                assert_error(self, merged_config(), f"{service}: missing from compose.yaml alone", base)
        merged = merged_config()
        merged["services"]["builder"] = {"build": {"context": "/repo"}}
        assert_error(self, merged, "expected ['backend', 'frontend']")

    def test_identity_variables_must_not_be_injected(self):
        for name in ("APP_VERSION", "GIT_SHA"):
            for service in ("backend", "frontend"):
                with self.subTest(name=name, service=service):
                    merged = merged_config()
                    merged["services"][service].setdefault("environment", {})[name] = "0.0.0"
                    assert_error(self, merged, f"{service}: environment sets {name}")
                    assert_error(self, merged, f"{service}: environment differs from compose.yaml")

    def test_inherited_semantics_must_be_unchanged(self):
        changes = {
            "environment": lambda s: s["backend"]["environment"].update(OLLAMA_HOST="http://elsewhere"),
            "healthcheck": lambda s: s["frontend"]["healthcheck"].update(retries=1),
            "networks": lambda s: s["backend"].update(networks={"app_network": None, "host": None}),
            "ports": lambda s: s["backend"]["ports"][0].update(published="5001"),
            "command": lambda s: s["backend"].update(command=["sh", "-c", "true"]),
            "env_file": lambda s: s["frontend"].update(env_file=["/srv/release.env"]),
            "volumes": lambda s: s["backend"]["volumes"][0].update(read_only=True),
        }
        for key, change in changes.items():
            with self.subTest(key=key):
                merged = merged_config()
                change(merged["services"])
                assert_error(self, merged, f"differs from compose.yaml")
                self.assertTrue(any(key in e for e in errors_for(merged)), errors_for(merged))

    def test_healthcheck_and_network_removal(self):
        merged = merged_config()
        merged["services"]["backend"]["healthcheck"] = {"disable": True}
        assert_error(self, merged, "backend: healthcheck missing or disabled")
        merged = merged_config()
        merged["services"]["frontend"]["healthcheck"]["test"] = ["NONE"]
        assert_error(self, merged, "frontend: healthcheck missing or disabled")
        merged = merged_config()
        del merged["services"]["frontend"]["healthcheck"]
        assert_error(self, merged, "frontend: healthcheck missing or disabled")
        merged = merged_config()
        merged["services"]["backend"]["networks"] = {}
        assert_error(self, merged, "backend: not attached to app_network")

    def test_top_level_changes(self):
        merged = merged_config()
        merged["networks"]["extra"] = {"name": "x"}
        assert_error(self, merged, "top-level networks differs from compose.yaml")
        merged = merged_config()
        merged["configs"] = {"c": {"file": "/etc/passwd"}}
        assert_error(self, merged, "top-level configs differs from compose.yaml")


class CheckRunTest(unittest.TestCase):
    def run_check(self, fake, root=REPO_ROOT):
        return check_release_compose(root, runner=fake)

    def test_valid_run_uses_only_compose_config(self):
        fake = FakeCompose()
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "t", "COMPOSE_FILE": "x.yaml",
                                          "BACKEND_PORT": "9", "APP_VERSION": "9.9.9"}):
            summary = self.run_check(fake)
        self.assertEqual(len(fake.calls), 4)
        files = [[c["command"][i + 1] for i, a in enumerate(c["command"]) if a == "-f"] for c in fake.calls]
        self.assertEqual(files, [[COMPOSE_FILE], [COMPOSE_FILE, RELEASE_OVERRIDE]] * 2)
        self.assertEqual([c["project"] for c in fake.calls],
                         [p for p in CHECK_PROJECTS for _ in range(2)])
        self.assertEqual(len(set(CHECK_PROJECTS)), 2)
        for call in fake.calls:
            command = call["command"]
            images = fake_image_refs(call["project"])
            self.assertEqual(command[:2], ["docker", "compose"])
            self.assertEqual(command[-3:], ["config", "--format", "json"])
            for verb in ("up", "build", "pull", "create", "run", "start"):
                self.assertNotIn(verb, command)
            self.assertEqual(call["cwd"], str(REPO_ROOT))
            self.assertLessEqual(set(call["env"]), {"PATH", "HOME", "DOCKER_CONFIG"})
            self.assertIn(f"RAG_BACKEND_IMAGE={images['backend']}\n", call["env_file"])
            self.assertIn(f"RAG_FRONTEND_IMAGE={images['frontend']}\n", call["env_file"])
            self.assertNotIn("APP_VERSION", call["env_file"])
            self.assertNotIn("GIT_SHA", call["env_file"])
        for project in CHECK_PROJECTS:
            result = summary["projects"][project]
            self.assertEqual(result["data_volume"]["name"], f"{project}_rag_data")
            self.assertEqual(result["network"], f"{project}_app_network")
            self.assertEqual(result["services"]["backend"]["image"], fake_image_refs(project)["backend"])
            self.assertEqual(result["services"]["frontend"]["host_ips"], ["127.0.0.1"])

    def test_names_pinned_to_one_project_are_caught(self):
        # An override pinning `volumes: {rag_data: {name: ...}}` (or the network
        # name) matches "<project>_rag_data" for one fixed project only.
        def pin_volume(doc, project):
            doc["volumes"]["rag_data"]["name"] = f"{CHECK_PROJECT}_rag_data"

        def pin_network(doc, project):
            doc["networks"]["app_network"]["name"] = f"{CHECK_PROJECT}_app_network"
        for mutate, fragment in ((pin_volume, "volume rag_data resolves to"),
                                 (pin_network, "network app_network is not project-scoped")):
            with self.subTest(fragment=fragment):
                with self.assertRaisesRegex(ComposeCheckError, f"project {CHECK_PROJECTS[1]}: .*{fragment}"):
                    self.run_check(FakeCompose(mutate=mutate))

    def test_needs_two_distinct_projects(self):
        for projects in ((CHECK_PROJECT,), (CHECK_PROJECT, CHECK_PROJECT), ()):
            with self.subTest(projects=projects):
                fake = FakeCompose()
                with self.assertRaisesRegex(ComposeCheckError, "two distinct"):
                    check_release_compose(REPO_ROOT, projects=projects, runner=fake)
                self.assertEqual(fake.calls, [])

    def test_fake_images_are_well_formed_digest_references(self):
        for service, ref in IMAGES.items():
            self.assertRegex(ref, r"^ghcr\.io/henric0612/rag-news-" + service + r"@sha256:[0-9a-f]{64}$")

    def test_violation_fails_the_run(self):
        def keep_build(doc, project):
            doc["services"]["backend"]["build"] = {"context": "/repo/Backend"}
        with self.assertRaisesRegex(ComposeCheckError, "backend: build is still configured"):
            self.run_check(FakeCompose(mutate=keep_build))

    def test_non_isolated_project_is_refused_before_running(self):
        fake = FakeCompose()
        with self.assertRaises(ComposeCheckError):
            check_release_compose(REPO_ROOT, projects=("rag-cd-x", "rag-news-intelligence-platform"),
                                  runner=fake)
        self.assertEqual(fake.calls, [])

    def test_compose_cli_missing(self):
        def missing(command, cwd, env):
            raise FileNotFoundError(2, "No such file or directory", "docker")
        with self.assertRaisesRegex(ComposeCheckError, "cannot run docker compose"):
            self.run_check(missing)

    def test_compose_exits_non_zero(self):
        def failing(command, cwd, env):
            return 1, "", "required variable RAG_FRONTEND_IMAGE is missing a value"
        with self.assertRaisesRegex(ComposeCheckError, "exited 1.*RAG_FRONTEND_IMAGE"):
            self.run_check(failing)

    def test_invalid_or_unexpected_output(self):
        for output in ("not json", "", "[]", '{"services": []}', '{"name": "x"}'):
            with self.subTest(output=output):
                with self.assertRaises(ComposeCheckError):
                    self.run_check(FakeCompose(merged=output))
                with self.assertRaises(ComposeCheckError):
                    self.run_check(FakeCompose(base=output))

    def test_missing_compose_files(self):
        for present in ((COMPOSE_FILE,), (RELEASE_OVERRIDE,), ()):
            with self.subTest(present=present), tempfile.TemporaryDirectory() as tmp:
                for name in present:
                    (Path(tmp) / name).parent.mkdir(parents=True, exist_ok=True)
                    (Path(tmp) / name).write_text("services: {}\n")
                fake = FakeCompose()
                with self.assertRaisesRegex(ComposeCheckError, "is missing from"):
                    check_release_compose(tmp, runner=fake)


class MainTest(unittest.TestCase):
    def run_main(self, runner, argv=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(compose_check.Path, "cwd", return_value=REPO_ROOT):
            code = compose_check.main(argv, runner=runner)
        return code, out.getvalue(), err.getvalue()

    def test_pass_exits_zero(self):
        code, out, _ = self.run_main(FakeCompose())
        self.assertEqual(code, 0)
        self.assertIn("all assertions passed", out)

    def test_failures_exit_non_zero(self):
        def pull_always(doc, project):
            doc["services"]["frontend"]["pull_policy"] = "always"
        for runner in (FakeCompose(mutate=pull_always), FakeCompose(merged="{"),
                       lambda c, cwd, env: (125, "", "unknown command: docker compose")):
            code, out, err = self.run_main(runner)
            self.assertEqual(code, 1)
            self.assertIn("error:", err)
            self.assertNotIn("all assertions passed", out)

    def test_arguments_are_rejected(self):
        code, _, _ = self.run_main(FakeCompose(), ["--skip"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
