"""Compose image-mode check: ``python3 -m deploy.rag_delivery.compose_check``.

Runs ``docker compose config`` (never ``up``, ``build`` or ``pull``) on
``compose.yaml`` alone and with ``deploy/compose.release.yaml``, using fake
digest references, under two isolated ``rag-cd-*`` project names, and
asserts on the merged JSON that both services run only the given digest-pinned images, are
never pulled or built, keep their loopback ports, and inherit everything
else from ``compose.yaml`` unchanged. Any failure, including a missing file
or Compose CLI, exits non-zero; nothing is skipped.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .contract import IMAGE_REPOSITORIES, SERVICES

COMPOSE_FILE = "compose.yaml"
RELEASE_OVERRIDE = "deploy/compose.release.yaml"
# Two names, so a data volume or network name pinned in the override cannot
# match "<project>_rag_data" by coincidence with a single fixed project.
CHECK_PROJECTS = ("rag-cd-compose-check", "rag-cd-compose-check-alt")
CHECK_PROJECT = CHECK_PROJECTS[0]
PROJECT_RE = re.compile(r"rag-cd-[a-z0-9][a-z0-9_-]*")
DIGEST_REF_RE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}")

IMAGE_VARIABLES = {"backend": "RAG_BACKEND_IMAGE", "frontend": "RAG_FRONTEND_IMAGE"}
IDENTITY_VARIABLES = ("APP_VERSION", "GIT_SHA")
TEST_ENV = {
    "SECRET_KEY": "rag-cd-compose-check-secret-key",
    "JWT_SECRET_KEY": "rag-cd-compose-check-jwt-key",
}
# Only what the docker CLI needs to find itself and its plugins; ambient
# COMPOSE_*, port, image or identity variables would override the env file.
PASSTHROUGH_ENV = ("PATH", "HOME", "DOCKER_CONFIG")

LOOPBACK = "127.0.0.1"
NETWORK = "app_network"
DATA_VOLUME = "rag_data"
DATA_TARGET = "/app/Backend/data"
# The only service keys the override may change: it removes build and sets these.
OVERRIDE_KEYS = ("image", "pull_policy")


class ComposeCheckError(RuntimeError):
    """The Compose release override does not satisfy the image-only contract."""


def fake_image_refs(project=CHECK_PROJECT):
    """Well-formed, obviously fake ``repository@sha256:<64 hex>`` references."""
    return {
        service: f"{IMAGE_REPOSITORIES[service]}@sha256:"
                 + hashlib.sha256(f"{project}/{service}".encode()).hexdigest()
        for service in SERVICES
    }


def require_project(project):
    if not isinstance(project, str) or not PROJECT_RE.fullmatch(project):
        raise ComposeCheckError(f"project {project!r} is not an isolated rag-cd-* project")
    return project


def compose_command(project, env_file, files):
    command = ["docker", "compose", "--env-file", str(env_file), "-p", project]
    for name in files:
        command += ["-f", name]
    return command + ["config", "--format", "json"]


def default_runner(command, cwd, env):
    """Run a command; return (returncode, stdout, stderr)."""
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def compose_config(root, project, files, variables, runner=default_runner):
    """Return the merged Compose configuration as parsed JSON."""
    for name in files:
        if not (Path(root) / name).is_file():
            raise ComposeCheckError(f"Compose file {name} is missing from {root}")
    env = {k: os.environ[k] for k in PASSTHROUGH_ENV if k in os.environ}
    with tempfile.TemporaryDirectory(prefix="rag-cd-compose-check-") as tmp:
        env_file = Path(tmp) / "check.env"
        env_file.write_text("".join(f"{k}={v}\n" for k, v in variables.items()))
        command = compose_command(project, env_file, files)
        try:
            returncode, stdout, stderr = runner(command, str(root), env)
        except OSError as error:
            raise ComposeCheckError(f"cannot run docker compose: {error}") from error
    if returncode != 0:
        raise ComposeCheckError(
            f"docker compose config exited {returncode} for {' '.join(files)}: {stderr.strip()}"
        )
    try:
        config = json.loads(stdout)
    except ValueError as error:
        raise ComposeCheckError(f"docker compose config output is not JSON: {error}") from error
    if not isinstance(config, dict) or not isinstance(config.get("services"), dict):
        raise ComposeCheckError("docker compose config output has no services mapping")
    return config


def _service_errors(service, merged, base, image):
    errors = []
    if "build" in merged:
        errors.append(f"{service}: build is still configured")
    if merged.get("image") != image:
        errors.append(f"{service}: image {merged.get('image')!r}, expected {image!r}")
    if not isinstance(merged.get("image"), str) or not DIGEST_REF_RE.fullmatch(merged["image"]):
        errors.append(f"{service}: image {merged.get('image')!r} is not a repository@sha256 digest reference")
    if merged.get("pull_policy") != "never":
        errors.append(f"{service}: pull_policy {merged.get('pull_policy')!r}, expected 'never'")

    ports = merged.get("ports")
    if not isinstance(ports, list) or not ports:
        errors.append(f"{service}: no published ports")
    else:
        for port in ports:
            if not isinstance(port, dict) or port.get("host_ip") != LOOPBACK:
                errors.append(f"{service}: port {port!r} is not bound to {LOOPBACK}")

    environment = merged.get("environment") or {}
    if not isinstance(environment, dict):
        errors.append(f"{service}: environment is not a mapping")
        environment = {}
    for name in IDENTITY_VARIABLES:
        if name in environment:
            errors.append(f"{service}: environment sets {name}, which would override the image identity")

    networks = merged.get("networks")
    if not isinstance(networks, dict) or NETWORK not in networks:
        errors.append(f"{service}: not attached to {NETWORK}")
    healthcheck = merged.get("healthcheck")
    if (not isinstance(healthcheck, dict) or healthcheck.get("disable")
            or not isinstance(healthcheck.get("test"), list) or not healthcheck["test"]
            or healthcheck["test"][0] == "NONE"):
        errors.append(f"{service}: healthcheck missing or disabled")

    # Inheritance: apart from build, image and pull_policy the release service
    # must be exactly the compose.yaml service.
    if not isinstance(base, dict):
        errors.append(f"{service}: missing from compose.yaml alone")
        return errors
    inherited = set(base) - {"build"} - set(OVERRIDE_KEYS)
    changed = set(merged) - set(OVERRIDE_KEYS)
    for key in sorted(inherited | changed):
        if key == "build":
            continue
        if merged.get(key, "<absent>") != base.get(key, "<absent>"):
            errors.append(f"{service}: {key} differs from compose.yaml")
    return errors


def _data_volume_errors(project, services, volumes):
    errors = []
    expected = f"{project}_{DATA_VOLUME}"
    mounts = (services.get("backend") or {}).get("volumes")
    data_mounts = [m for m in mounts or [] if isinstance(m, dict) and m.get("target") == DATA_TARGET]
    if len(data_mounts) != 1:
        errors.append(f"backend: expected one mount at {DATA_TARGET}, found {len(data_mounts)}")
    else:
        mount = data_mounts[0]
        if mount.get("type") != "volume" or mount.get("source") != DATA_VOLUME:
            errors.append(
                f"backend: {DATA_TARGET} is a {mount.get('type')!r} mount of {mount.get('source')!r}, "
                f"expected named volume {DATA_VOLUME!r}"
            )
    for service, value in services.items():
        for mount in (value or {}).get("volumes") or []:
            if isinstance(mount, dict) and mount.get("source") == DATA_VOLUME and service != "backend":
                errors.append(f"{service}: mounts {DATA_VOLUME}")
    volume = (volumes or {}).get(DATA_VOLUME) if isinstance(volumes, dict) else None
    if not isinstance(volume, dict):
        errors.append(f"top-level volume {DATA_VOLUME} is not declared")
    else:
        if volume.get("name") != expected:
            errors.append(f"volume {DATA_VOLUME} resolves to {volume.get('name')!r}, expected {expected!r}")
        if volume.get("external"):
            errors.append(f"volume {DATA_VOLUME} is external, not project-scoped")
    return errors


def release_config_errors(merged, base, project, images):
    """All violations of the image-only contract in the merged configuration."""
    errors = []
    if merged.get("name") != project:
        errors.append(f"merged project name {merged.get('name')!r}, expected {project!r}")
    services = merged.get("services") or {}
    base_services = base.get("services") or {}
    if set(services) != set(SERVICES):
        errors.append(f"services {sorted(services)}, expected {sorted(SERVICES)}")
    for service in SERVICES:
        if not isinstance(services.get(service), dict):
            errors.append(f"{service}: missing from the merged configuration")
            continue
        errors += _service_errors(service, services[service], base_services.get(service), images[service])
    errors += _data_volume_errors(project, services, merged.get("volumes"))
    networks = merged.get("networks")
    network = networks.get(NETWORK) if isinstance(networks, dict) else None
    if not isinstance(network, dict) or network.get("name") != f"{project}_{NETWORK}":
        errors.append(f"network {NETWORK} is not project-scoped as {project}_{NETWORK}")
    for key in sorted((set(merged) | set(base)) - {"services"}):
        if merged.get(key) != base.get(key):
            errors.append(f"top-level {key} differs from compose.yaml")
    return errors


def _check_project(root, project, runner):
    images = fake_image_refs(project)
    variables = dict(TEST_ENV)
    variables.update({IMAGE_VARIABLES[s]: images[s] for s in SERVICES})
    base = compose_config(root, project, (COMPOSE_FILE,), variables, runner)
    merged = compose_config(root, project, (COMPOSE_FILE, RELEASE_OVERRIDE), variables, runner)
    errors = release_config_errors(merged, base, project, images)
    if errors:
        raise ComposeCheckError(f"project {project}: " + "; ".join(errors))
    services = merged["services"]
    return {
        "services": {
            s: {
                "image": services[s]["image"],
                "pull_policy": services[s]["pull_policy"],
                "build": "absent",
                "host_ips": sorted({p["host_ip"] for p in services[s]["ports"]}),
            }
            for s in SERVICES
        },
        "data_volume": {"source": DATA_VOLUME, "name": merged["volumes"][DATA_VOLUME]["name"]},
        "network": merged["networks"][NETWORK]["name"],
    }


def check_release_compose(root, projects=CHECK_PROJECTS, runner=default_runner):
    """Run both Compose configurations per project and assert the contract; return a summary."""
    projects = tuple(require_project(p) for p in projects)
    if len(set(projects)) < 2:
        raise ComposeCheckError(f"need at least two distinct rag-cd-* projects, got {list(projects)}")
    return {
        "command": " ".join(compose_command("<project>", "<check.env>", (COMPOSE_FILE, RELEASE_OVERRIDE))),
        "projects": {project: _check_project(root, project, runner) for project in projects},
    }


def main(argv=None, runner=default_runner):
    if argv:
        print(f"usage: python3 -m deploy.rag_delivery.compose_check (no arguments, got {argv})",
              file=sys.stderr)
        return 2
    try:
        summary = check_release_compose(Path.cwd(), runner=runner)
    except ComposeCheckError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("compose image-only release mode: all assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
