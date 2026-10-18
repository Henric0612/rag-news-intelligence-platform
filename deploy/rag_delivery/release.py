"""Release job steps (tag path only), in the frozen order of plan §5.2.

① resolve registry tags and digests, ② build and validate the manifest
(see manifest.py), ③ anonymous pull check, ④ existing-release state,
⑤ create a draft and upload assets, ⑥ download and verify, ⑦ publish,
⑧ read back. Steps ①–④ never create a Release object.
"""

import json
import re

from .contract import (
    GATE_EVIDENCE_NAME,
    MANIFEST_NAME,
    RELEASE_ASSETS,
    SERVICES,
    SUMS_NAME,
    identity_label_errors,
)
from .gate import GateError, peel_tag
from .manifest import companion_errors, manifest_errors, sums_errors
from .registry import RegistryError

MARKER_RE = re.compile(r"<!-- rag-delivery:release-run-id=([0-9]+) -->")
ASSET_TYPES = {
    MANIFEST_NAME: "application/json",
    GATE_EVIDENCE_NAME: "application/json",
    SUMS_NAME: "text/plain",
}


class ReleaseError(RuntimeError):
    """A release step failed; the run must stop."""


def verify_tag(github, tag, commit_sha, tag_object_sha):
    """Re-peel the protected tag; it must still name the gated commit."""
    status, ref_doc = github.get_optional(f"git/ref/tags/{tag}")
    if status != 200:
        raise ReleaseError(f"tag {tag} not found")
    target = (ref_doc.get("object") or {}).get("sha")
    tag_doc = github.json("GET", f"git/tags/{target}") if (ref_doc.get("object") or {}).get("type") == "tag" else None
    try:
        peeled = peel_tag(ref_doc, tag_doc, tag)
    except GateError as error:
        raise ReleaseError(str(error)) from error
    if peeled != (commit_sha, tag_object_sha):
        raise ReleaseError(f"tag {tag} peels to {peeled}, gate recorded {(commit_sha, tag_object_sha)}")


def cross_check_digests(images, expected):
    """Compare registry digests with upstream job outputs when those outputs exist."""
    for service in SERVICES:
        upstream = expected.get(service) or ""
        if not upstream:
            print(f"{service}: no upstream digest output available; registry value used alone")
            continue
        if images[service]["digest"] != upstream:
            raise ReleaseError(f"{service}: registry digest {images[service]['digest']} != build-push output {upstream}")


def anonymous_pull_errors(registry, manifest):
    """③ Both release images must be pullable without credentials, labels intact."""
    errors = []
    for service in SERVICES:
        image = manifest["images"][service]
        token = registry.token(image["repository"])
        if not token:
            errors.append(
                f"{image['repository']}: anonymous pull denied; the package is not public "
                "(expected on the first release until P1, see plan §5.5)"
            )
            continue
        try:
            description = registry.describe(image["repository"], image["digest"], token)
        except RegistryError as error:
            errors.append(f"{image['ref']}: anonymous pull failed: {error}")
            continue
        if description["digest"] != image["digest"]:
            errors.append(f"{image['ref']}: anonymous digest {description['digest']}")
        errors += identity_label_errors(
            service, description["labels"], manifest["app_version"], manifest["commit_sha"]
        )
    return errors


def release_notes(manifest, run_id):
    images = "\n".join(f"- {service}: `{manifest['images'][service]['ref']}`" for service in SERVICES)
    return (
        f"Release {manifest['tag']} of {manifest['project']}.\n\n"
        f"Commit: `{manifest['commit_sha']}`\n\n{images}\n\n"
        f"Verify `{SUMS_NAME}` before trusting `{MANIFEST_NAME}` or `{GATE_EVIDENCE_NAME}`; "
        "deploy only by digest. See Docs/Phase-E-Delivery.md.\n\n"
        f"<!-- rag-delivery:release-run-id={run_id} -->\n"
    )


def marker_run_id(body):
    match = MARKER_RE.search(body or "")
    return match.group(1) if match else None


def drafts_to_delete(releases, tag, run_id):
    """④ Decide what to do with existing releases for ``tag``.

    A published release fails the run. A draft is deleted only when its
    marker names this same workflow run (left by an earlier attempt after
    step ⑤); any other draft fails the run without deleting anything.
    """
    matching = [r for r in releases if r.get("tag_name") == tag]
    published = [r for r in matching if r.get("draft") is not True]
    if published:
        raise ReleaseError(f"release {tag} already exists and is not a draft (id {published[0].get('id')})")
    foreign = [r for r in matching if marker_run_id(r.get("body")) != str(run_id)]
    if foreign:
        raise ReleaseError(
            f"draft release(s) for {tag} not created by run {run_id}: "
            + ", ".join(str(r.get("id")) for r in foreign)
        )
    return [r["id"] for r in matching]


def check_release_state(github, tag, run_id):
    status, _ = github.get_optional(f"releases/tags/{tag}")
    if status == 200:
        raise ReleaseError(f"published release {tag} already exists")
    for release_id in drafts_to_delete(github.paginate("releases"), tag, run_id):
        response = github.request("DELETE", f"releases/{release_id}")
        if response.status != 204:
            raise ReleaseError(f"could not delete same-run draft {release_id}: HTTP {response.status}")
        print(f"deleted draft {release_id} left by an earlier attempt of run {run_id}")
    if [r for r in github.paginate("releases") if r.get("tag_name") == tag]:
        raise ReleaseError(f"a release object for {tag} still exists")


def create_draft(github, manifest, run_id, files):
    """⑤ Create the draft for the existing tag and upload the three assets."""
    tag = manifest["tag"]
    status, _ = github.get_optional(f"git/ref/tags/{tag}")
    if status != 200:
        raise ReleaseError(f"tag {tag} must exist before a release is created")
    release = github.json("POST", "releases", {
        "tag_name": tag,
        "name": tag,
        "body": release_notes(manifest, run_id),
        "draft": True,
    }, expect=(201,))
    if release.get("draft") is not True or release.get("tag_name") != tag:
        raise ReleaseError(f"created release {release.get('id')} is not a draft for {tag}")
    for name in RELEASE_ASSETS:
        github.upload_asset(release["upload_url"], name, files[name], ASSET_TYPES[name])
    print(f"draft release {release['id']} created with {len(RELEASE_ASSETS)} assets")
    return release["id"]


def asset_set_errors(release):
    names = sorted(a.get("name") for a in release.get("assets", []))
    errors = []
    if names != sorted(RELEASE_ASSETS):
        errors.append(f"release assets {names} != {sorted(RELEASE_ASSETS)}")
    errors += [f"asset {a.get('name')} state {a.get('state')}" for a in release.get("assets", [])
               if a.get("state") != "uploaded"]
    return errors


def downloaded_errors(local, downloaded):
    """⑥ The downloaded assets must equal the local files and verify on their own."""
    errors = [f"{name}: downloaded bytes differ from the uploaded file"
              for name in RELEASE_ASSETS if downloaded.get(name) != local.get(name)]
    try:
        sums = downloaded[SUMS_NAME].decode("utf-8")
        errors += sums_errors(sums, downloaded)
        if errors:
            return errors
        manifest = json.loads(downloaded[MANIFEST_NAME])
        evidence = json.loads(downloaded[GATE_EVIDENCE_NAME])
    except (KeyError, UnicodeDecodeError, ValueError) as error:
        return errors + [f"downloaded assets unreadable: {error!r}"]
    errors += manifest_errors(manifest)
    errors += companion_errors(manifest, evidence)
    return errors


def verify_draft(github, release_id, tag, local):
    release = github.json("GET", f"releases/{release_id}")
    errors = asset_set_errors(release)
    if release.get("draft") is not True or release.get("tag_name") != tag:
        errors.append(f"release {release_id} is not the draft for {tag}")
    if errors:
        raise ReleaseError("; ".join(errors))
    downloaded = {a["name"]: github.download_asset(a["id"]) for a in release["assets"]}
    errors = downloaded_errors(local, downloaded)
    if errors:
        raise ReleaseError("; ".join(errors))
    print(f"draft {release_id}: assets downloaded, SHA256SUMS and manifest verified")


def published_errors(release, release_id, tag):
    """⑧ Read-back conditions for the published release."""
    errors = asset_set_errors(release)
    if release.get("id") != release_id:
        errors.append(f"published release id {release.get('id')} != draft {release_id}")
    if release.get("tag_name") != tag:
        errors.append(f"published tag {release.get('tag_name')} != {tag}")
    if release.get("draft") is not False:
        errors.append("release is still a draft")
    if release.get("immutable") is not True:
        errors.append(f"release immutable={release.get('immutable')!r}, expected true")
    return errors


def publish(github, release_id, tag, commit_sha, tag_object_sha):
    github.json("PATCH", f"releases/{release_id}", {"draft": False})
    status, release = github.get_optional(f"releases/tags/{tag}")
    if status != 200:
        raise ReleaseError(f"published release {tag} not readable")
    errors = published_errors(release, release_id, tag)
    if errors:
        raise ReleaseError("published but read-back failed (INCOMPLETE, Human Review): " + "; ".join(errors))
    verify_tag(github, tag, commit_sha, tag_object_sha)
    print(f"release {tag} published: draft=false, immutable=true, tag still peels to {commit_sha}")
