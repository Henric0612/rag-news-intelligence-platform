"""Build, inspect and (tag path only) push the release images.

The same build and inspection code serves the tag path (``build-push``) and
the dispatch dry run (``build-dry-run``). Pushing is a separate function that
only the tag path calls, and it refuses to push anything unless an
authenticated lookup confirms that all four target tags are absent.
"""

import fnmatch
import hashlib
import json
import re
import subprocess
import tarfile
import time
from pathlib import Path

from .contract import (
    BASE_IMAGES,
    BUILD_EVIDENCE_SCHEMA_VERSION,
    DATA_FORMAT_VERSION,
    IMAGE_REPOSITORIES,
    INPUT_FILES,
    PLATFORM,
    SERVICES,
    identity_label_errors,
    is_commit_sha,
    is_digest,
    push_order,
    require_commit_sha,
    require_version,
)
from .registry import RegistryError, prepush_blockers, release_tag_states, resolve_release_images
from .transport import TransportError

FORBIDDEN_NAME_PATTERNS = (".env*", "*.db", "*.sqlite*", "*.index", "id_mapping.json")
SERVICE_BUILD = {
    "backend": ("Backend/Dockerfile", "Backend"),
    "frontend": ("Frontend/Dockerfile", "Frontend"),
}
MODEL_ARGS = {"EMBEDDING_REVISION": "embedding", "RERANK_REVISION": "reranker"}
DECLARED_SCHEMA_SCRIPT = Path(__file__).with_name("declared_schema.py")
READBACK_ATTEMPTS = 3
READBACK_DELAY_SECONDS = 10


class BuildError(RuntimeError):
    """Image build, inspection or push failed a release condition."""


def run_command(args, stdin_text=None):
    """Run a command, streaming stderr; return stdout or raise BuildError."""
    result = subprocess.run(args, input=stdin_text, stdout=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise BuildError(f"{' '.join(args[:3])} ... exited {result.returncode}")
    return result.stdout


def content_violations(names):
    """Filesystem paths that must never ship in a release image."""
    violations = []
    for name in names:
        parts = [p for p in name.split("/") if p not in ("", ".")]
        if not parts:
            continue
        path = "/".join(parts)
        for pattern in FORBIDDEN_NAME_PATTERNS:
            if fnmatch.fnmatchcase(parts[-1], pattern):
                violations.append(f"/{path}: forbidden name ({pattern})")
                break
        if "uploads" in parts[:-1]:
            violations.append(f"/{path}: content under an uploads/ directory")
    return violations


def export_names(image, run=run_command):
    """List every path in the image filesystem via docker create + export."""
    container = run(["docker", "create", image]).strip()
    try:
        process = subprocess.Popen(["docker", "export", container], stdout=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                names = [member.name for member in archive]
        finally:
            process.stdout.close()
            returncode = process.wait()
        if returncode != 0:
            raise BuildError(f"docker export {container} exited {returncode}")
    finally:
        run(["docker", "rm", container])
    return names


def parse_models(dockerfile_text):
    """Model ids and revisions pinned by the Backend Dockerfile build arguments."""
    args = dict(re.findall(r"^ARG\s+([A-Z_]+)=(\S+)\s*$", dockerfile_text, re.MULTILINE))
    calls = re.findall(r"snapshot_download\('([^']+)',\s*revision='\$\{([A-Z_]+)\}'", dockerfile_text)
    models = {}
    for model_id, variable in calls:
        role = MODEL_ARGS.get(variable)
        if role is None or role in models:
            raise BuildError(f"unexpected model download for {variable}")
        revision = args.get(variable)
        if not is_commit_sha(revision):
            raise BuildError(f"{variable} has no pinned 40-character revision")
        models[role] = {"id": model_id, "revision": revision}
    if set(models) != set(MODEL_ARGS.values()):
        raise BuildError(f"Backend/Dockerfile pins models {sorted(models)}, expected embedding and reranker")
    return models


def file_hashes(source_dir):
    root = Path(source_dir)
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in INPUT_FILES}


def repo_digest(image_ref, repo_digests):
    """The digest of ``image_ref`` (e.g. python:3.13-slim) from its RepoDigests."""
    name = image_ref.rsplit(":", 1)[0]
    matches = [d.split("@", 1)[1] for d in repo_digests or [] if d.startswith(f"{name}@")]
    if len(matches) != 1 or not is_digest(matches[0]):
        raise BuildError(f"cannot resolve a single digest for {image_ref}: {repo_digests}")
    return matches[0]


def image_identity_errors(service, inspect, app_version, commit_sha):
    """Read back platform, OCI identity labels and (Backend) runtime ENV."""
    config = inspect.get("Config") or {}
    errors = identity_label_errors(service, config.get("Labels"), app_version, commit_sha)
    platform = f"{inspect.get('Os')}/{inspect.get('Architecture')}"
    if platform != PLATFORM:
        errors.append(f"{service}: platform {platform}, expected {PLATFORM}")
    if service == "backend":
        env = set(config.get("Env") or [])
        for line in (f"APP_VERSION={app_version}", f"GIT_SHA={commit_sha}"):
            if line not in env:
                errors.append(f"backend: runtime ENV lacks {line}")
    return errors


def declared_schema_fingerprint(image, run=run_command):
    output = run(
        ["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "python", image, "-"],
        stdin_text=DECLARED_SCHEMA_SCRIPT.read_text(),
    )
    lines = [line for line in output.splitlines() if line.strip()]
    try:
        result = json.loads(lines[-1])
    except (IndexError, ValueError) as error:
        raise BuildError("declared schema script produced no JSON result") from error
    fingerprint = result.get("declared_schema_fingerprint")
    if not is_digest(fingerprint) or not result.get("tables"):
        raise BuildError(f"invalid declared schema result {result!r}")
    return fingerprint, result["tables"]


def local_tags(service, version, commit_sha):
    return [f"{IMAGE_REPOSITORIES[service]}:{tag}" for tag in push_order(version, commit_sha)]


def build_release_images(source_dir, version, commit_sha, context, run=run_command,
                         list_names=export_names):
    """Build both images and return build evidence; raise BuildError on any violation.

    ``context`` carries the Actions identity (release_run_id, run_attempt,
    workflow_ref, runner) and a ``now`` callable.
    """
    app_version = require_version(version)
    require_commit_sha(commit_sha)
    source = Path(source_dir)

    base_images = {}
    for image in BASE_IMAGES:
        run(["docker", "pull", "--platform", PLATFORM, image])
        digests = json.loads(run(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image]))
        base_images[image] = repo_digest(image, digests)

    evidence_images = {}
    data_compat = None
    for service in SERVICES:
        dockerfile, context_dir = SERVICE_BUILD[service]
        tags = local_tags(service, version, commit_sha)
        command = ["docker", "build", "--pull", "--platform", PLATFORM, "--progress=plain",
                   "--build-arg", f"APP_VERSION={app_version}", "--build-arg", f"GIT_SHA={commit_sha}"]
        for tag in tags:
            command += ["--tag", tag]
        run(command + ["--file", str(source / dockerfile), str(source / context_dir)])

        inspect = json.loads(run(["docker", "image", "inspect", tags[0]]))[0]
        errors = image_identity_errors(service, inspect, app_version, commit_sha)
        names = list_names(tags[0])
        if not names:
            errors.append(f"{service}: image filesystem listing is empty")
        violations = content_violations(names)
        errors += [f"{service}: {v}" for v in violations]
        if errors:
            raise BuildError("; ".join(errors))

        evidence_images[service] = {
            "repository": IMAGE_REPOSITORIES[service],
            "local_tags": tags,
            "image_id": inspect["Id"],
            "uncompressed_size_bytes": inspect["Size"],
            "platform": PLATFORM,
            "labels": (inspect.get("Config") or {}).get("Labels") or {},
            "content_check": {
                "forbidden_patterns": list(FORBIDDEN_NAME_PATTERNS) + ["uploads/* (non-empty)"],
                "entries_scanned": len(names),
                "violations": violations,
            },
        }
        if service == "backend":
            fingerprint, tables = declared_schema_fingerprint(tags[0], run)
            evidence_images[service]["declared_schema_tables"] = tables
            models = parse_models((source / "Backend/Dockerfile").read_text())
            data_compat = {
                "declared_schema_fingerprint": fingerprint,
                "embedding": dict(models["embedding"]),
                "data_format_version": DATA_FORMAT_VERSION,
            }
        print(f"{service}: built {inspect['Id']}, identity labels verified, "
              f"{len(names)} paths scanned, no forbidden content")

    return {
        "schema_version": BUILD_EVIDENCE_SCHEMA_VERSION,
        "tag": version,
        "app_version": app_version,
        "commit_sha": commit_sha,
        "build": {
            "release_run_id": context["release_run_id"],
            "run_attempt": context["run_attempt"],
            "workflow_ref": context["workflow_ref"],
            "runner": context["runner"],
            "docker_version": run(["docker", "version", "--format", "{{.Server.Version}}"]).strip(),
            "built_at": context["now"](),
        },
        "inputs": {
            "base_images": base_images,
            "models": parse_models((source / "Backend/Dockerfile").read_text()),
            "files": file_hashes(source),
        },
        "data_compat": data_compat,
        "images": evidence_images,
    }


def push_release_images(registry, version, commit_sha, run=run_command, sleep=time.sleep):
    """Tag path only: confirm absence, push in frozen order, read back digests.

    ``registry`` must be an authenticated RegistryClient. Nothing is pushed
    unless all four target tags are confirmed NOT_FOUND by authenticated
    lookups; EXISTS, UNKNOWN, denied or failed lookups all stop here.
    """
    states = release_tag_states(registry, version, commit_sha, actions="pull,push")
    for state in states:
        print(f"pre-push {state.repository}:{state.tag}: {state.state} ({state.detail})")
    blockers = prepush_blockers(states)
    if blockers:
        raise BuildError("refusing to push: " + "; ".join(blockers))

    for tag in push_order(version, commit_sha):
        for service in SERVICES:
            run(["docker", "push", f"{IMAGE_REPOSITORIES[service]}:{tag}"])

    # Bounded retry for transient registry errors only: after a complete push,
    # a failed job cannot be resumed (a rerun stops at the pre-push check).
    for attempt in range(1, READBACK_ATTEMPTS + 1):
        try:
            images = resolve_release_images(registry, version, commit_sha)
            break
        except (RegistryError, TransportError) as error:
            if attempt == READBACK_ATTEMPTS:
                raise BuildError(f"post-push read-back failed after {attempt} attempts: {error}") from error
            print(f"post-push read-back attempt {attempt} failed ({error}); retrying")
            sleep(READBACK_DELAY_SECONDS)
    for service in SERVICES:
        local = json.loads(run(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}",
                                local_tags(service, version, commit_sha)[0]]))
        if images[service]["ref"] not in (local or []):
            raise BuildError(f"{service}: registry {images[service]['ref']} not in local RepoDigests {local}")
        print(f"{service}: both tags resolve to {images[service]['digest']}")
    return {"prepush": [s.as_dict() for s in states], "images": images}
