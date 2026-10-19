"""Command line entry point: ``python3 -m deploy.rag_delivery <command>``.

Commands map to release workflow steps; each exits non-zero on any failed
condition so the workflow stops.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .build import BuildError, build_release_images, push_release_images
from .contract import (
    GATE_EVIDENCE_NAME,
    MANIFEST_NAME,
    REPOSITORY,
    SERVICES,
    SUMS_NAME,
    ContractError,
)
from .gate import GateError, GateIO, default_test_runner, run_gate
from .github import GitHubClient, GitHubError
from .layers import LayerError, layer_evidence
from .licenses import LicenseError, build_inventory
from .manifest import (
    ManifestError,
    build_manifest,
    companion_errors,
    manifest_errors,
    render_sums,
    sums_errors,
)
from .preview import PreviewError, build_preview
from .public_probe import ProbeError, run_probe
from .registry import RegistryClient, RegistryError, resolve_release_images
from .release import (
    ReleaseError,
    anonymous_pull_errors,
    check_release_state,
    create_draft,
    cross_check_digests,
    publish,
    verify_draft,
    verify_tag,
)
from .transport import TransportError

FAILURES = (BuildError, ContractError, GateError, GitHubError, LayerError, LicenseError,
            ManifestError, PreviewError, ProbeError, RegistryError, ReleaseError, TransportError)


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def set_outputs(**values):
    target = os.environ.get("GITHUB_OUTPUT")
    for key, value in values.items():
        print(f"output {key}={value}")
    if target:
        with open(target, "a") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")


def github_client():
    return GitHubClient(os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", REPOSITORY))


def registry_credentials():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RegistryError("GITHUB_TOKEN is required for authenticated registry access")
    return (os.environ.get("GITHUB_ACTOR") or "github-actions", token)


def git(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, text=True)
    return result.returncode, result.stdout


def run_id_from_env():
    return int(os.environ["GITHUB_RUN_ID"])


def cmd_gate(args):
    io = GateIO(github=github_client(), registry=RegistryClient(), git=git,
                run_tests=default_test_runner, now=utc_now)
    evidence = run_gate(os.environ, io, args.source_dir)
    write_json(args.evidence, evidence)
    set_outputs(sha=evidence["commit_sha"], version=evidence["tag"],
                app_version=evidence["app_version"],
                tag_object_sha=evidence["tag_object_sha"] or "")
    print(f"gate passed for {evidence['tag']} at {evidence['commit_sha']}")


def cmd_build(args):
    context = {
        "release_run_id": run_id_from_env(),
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "workflow_ref": os.environ["GITHUB_WORKFLOW_REF"],
        "runner": " ".join(filter(None, (
            f"{os.environ.get('RUNNER_OS', '')}/{os.environ.get('RUNNER_ARCH', '')}",
            os.environ.get("ImageOS"), os.environ.get("ImageVersion")))),
        "now": utc_now,
    }
    evidence = build_release_images(args.source_dir, args.version, args.sha, context)
    write_json(args.evidence, evidence)


def cmd_public_probe(args):
    evidence, errors = run_probe(utc_now)
    write_json(args.out, evidence)
    if errors:
        raise ProbeError("; ".join(errors))
    print(f"anonymous read of {evidence['reference']} reproduced every pinned value")


def cmd_layers(args):
    write_json(args.out, layer_evidence(read_json(args.build_evidence), utc_now))


def cmd_license_inventory(args):
    inventory = build_inventory(args.source_dir, read_json(args.build_evidence), utc_now)
    write_json(args.out, inventory)
    summary = inventory["summary"]
    print(f"license inventory collected: {summary['findings']} findings for Human Review "
          f"{summary['by_category']}; conclusion {inventory['conclusion']}")


def cmd_push(args):
    registry = RegistryClient(credentials=registry_credentials())
    result = push_release_images(registry, args.version, args.sha)
    write_json(args.out, result)
    set_outputs(**{f"{s}_digest": result["images"][s]["digest"] for s in SERVICES})


def cmd_release_resolve(args):
    gate = read_json(args.gate_evidence)
    build = read_json(args.build_evidence)
    if build["build"]["release_run_id"] != run_id_from_env():
        raise ReleaseError("build evidence comes from a different workflow run")
    if (build["tag"], build["commit_sha"]) != (gate["tag"], gate["commit_sha"]):
        raise ReleaseError("build evidence identity differs from gate evidence")
    verify_tag(github_client(), gate["tag"], gate["commit_sha"], gate["tag_object_sha"])
    images = resolve_release_images(RegistryClient(credentials=registry_credentials()),
                                    gate["tag"], gate["commit_sha"])
    cross_check_digests(images, {"backend": args.backend_digest, "frontend": args.frontend_digest})
    for service in SERVICES:
        print(f"{service}: {images[service]['tags']} -> {images[service]['digest']} "
              f"({images[service]['media_type']})")
    write_json(args.out, images)


def cmd_manifest_build(args):
    gate_bytes = Path(args.gate_evidence).read_bytes()
    manifest = build_manifest(json.loads(gate_bytes), read_json(args.build_evidence),
                              read_json(args.registry_images))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / MANIFEST_NAME, manifest)
    (out / GATE_EVIDENCE_NAME).write_bytes(gate_bytes)
    files = {name: (out / name).read_bytes() for name in (MANIFEST_NAME, GATE_EVIDENCE_NAME)}
    (out / SUMS_NAME).write_text(render_sums(files))
    _validate_dir(out)
    print(f"manifest for {manifest['tag']} written and validated in {out}")


def cmd_manifest_preview(args):
    preview = build_preview(read_json(args.gate_evidence), read_json(args.build_evidence),
                            read_json(args.layer_evidence))
    write_json(args.out, preview)
    print(f"release preview for {preview['tag']} written; deployable=false, "
          f"{len(preview['pending_until_push'])} fields pending until push")


def _validate_dir(directory):
    directory = Path(directory)
    files = {name: (directory / name).read_bytes() for name in (MANIFEST_NAME, GATE_EVIDENCE_NAME)}
    errors = sums_errors((directory / SUMS_NAME).read_text(), files)
    if not errors:
        manifest = json.loads(files[MANIFEST_NAME])
        errors = manifest_errors(manifest) + companion_errors(manifest, json.loads(files[GATE_EVIDENCE_NAME]))
    if errors:
        raise ManifestError(errors)


def cmd_manifest_validate(args):
    if args.assets_dir:
        _validate_dir(args.assets_dir)
        print(f"release assets in {args.assets_dir} are valid")
        return
    errors = manifest_errors(read_json(args.manifest))
    if errors:
        raise ManifestError(errors)
    print(f"{args.manifest} is a valid release manifest")


def cmd_anonymous_check(args):
    errors = anonymous_pull_errors(RegistryClient(), read_json(args.manifest))
    if errors:
        raise ReleaseError("; ".join(errors))
    print("both release images are anonymously pullable with matching identity labels")


def _assets(directory):
    return {name: (Path(directory) / name).read_bytes() for name in (MANIFEST_NAME, GATE_EVIDENCE_NAME, SUMS_NAME)}


def cmd_release_state(args):
    check_release_state(github_client(), args.tag, run_id_from_env())
    print(f"no release object exists for {args.tag}")


def cmd_release_draft(args):
    _validate_dir(args.assets_dir)
    manifest = read_json(Path(args.assets_dir) / MANIFEST_NAME)
    release_id = create_draft(github_client(), manifest, run_id_from_env(), _assets(args.assets_dir))
    set_outputs(release_id=release_id)


def cmd_release_verify(args):
    manifest = read_json(Path(args.assets_dir) / MANIFEST_NAME)
    verify_draft(github_client(), args.release_id, manifest["tag"], _assets(args.assets_dir))


def cmd_release_publish(args):
    manifest = read_json(Path(args.assets_dir) / MANIFEST_NAME)
    publish(github_client(), args.release_id, manifest["tag"], manifest["commit_sha"],
            manifest["tag_object_sha"])


def parser():
    root = argparse.ArgumentParser(prog="python3 -m deploy.rag_delivery")
    sub = root.add_subparsers(dest="command", required=True)

    p = sub.add_parser("gate", help="run the release gate (env-driven)")
    p.add_argument("--source-dir", required=True, help="checkout of the exact SHA")
    p.add_argument("--evidence", required=True)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("build", help="build and inspect both images (no push)")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--evidence", required=True)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("public-probe", help="dry run: anonymous read probe of a pinned public GHCR image")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_public_probe)

    p = sub.add_parser("layers", help="dry run: build-side local layer sizes (docker history)")
    p.add_argument("--build-evidence", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_layers)

    p = sub.add_parser("license-inventory", help="dry run: read-only third-party license inventory")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--build-evidence", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_license_inventory)

    p = sub.add_parser("push", help="tag path: confirm absence, push, read back")
    p.add_argument("--version", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("release-resolve", help="step 1: resolve tags and digests from the registry")
    p.add_argument("--gate-evidence", required=True)
    p.add_argument("--build-evidence", required=True)
    p.add_argument("--backend-digest", default="")
    p.add_argument("--frontend-digest", default="")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_release_resolve)

    manifest = sub.add_parser("manifest", help="release manifest tools")
    msub = manifest.add_subparsers(dest="manifest_command", required=True)
    p = msub.add_parser("build", help="step 2: build, checksum and validate release assets")
    p.add_argument("--gate-evidence", required=True)
    p.add_argument("--build-evidence", required=True)
    p.add_argument("--registry-images", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=cmd_manifest_build)
    p = msub.add_parser("preview", help="dry run: build a non-deployable release-preview document")
    p.add_argument("--gate-evidence", required=True)
    p.add_argument("--build-evidence", required=True)
    p.add_argument("--layer-evidence", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_manifest_preview)
    p = msub.add_parser("validate", help="validate a manifest or a directory of release assets")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest")
    group.add_argument("--assets-dir")
    p.set_defaults(func=cmd_manifest_validate)

    p = sub.add_parser("anonymous-check", help="step 3: anonymous pull check")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=cmd_anonymous_check)

    p = sub.add_parser("release-state", help="step 4: reject existing releases, clear same-run drafts")
    p.add_argument("--tag", required=True)
    p.set_defaults(func=cmd_release_state)

    p = sub.add_parser("release-draft", help="step 5: create the draft and upload assets")
    p.add_argument("--assets-dir", required=True)
    p.set_defaults(func=cmd_release_draft)

    p = sub.add_parser("release-verify", help="step 6: download and verify draft assets")
    p.add_argument("--assets-dir", required=True)
    p.add_argument("--release-id", required=True, type=int)
    p.set_defaults(func=cmd_release_verify)

    p = sub.add_parser("release-publish", help="steps 7-8: publish and read back")
    p.add_argument("--assets-dir", required=True)
    p.add_argument("--release-id", required=True, type=int)
    p.set_defaults(func=cmd_release_publish)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except FAILURES as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
