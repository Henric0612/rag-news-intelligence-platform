"""Release gate: decide whether an exact commit may be released.

The pure functions take GitHub API JSON and return decisions or raise
GateError. ``run_gate`` wires them together with injected I/O so the whole
gate can be exercised with fixtures.
"""

import os
import subprocess
from dataclasses import dataclass

from .contract import (
    CHECK_APP_ID,
    CHECK_APP_SLUG,
    CI_WORKFLOW_PATH,
    GATE_EVIDENCE_SCHEMA_VERSION,
    MAIN_BRANCH,
    REPOSITORY,
    REQUIRED_CHECKS,
    ContractError,
    require_commit_sha,
    require_version,
)
from .registry import EXISTS, NOT_FOUND, gate_conflicts, release_tag_states

DELIVERY_TEST_COMMAND = ("python3", "-m", "unittest", "discover", "deploy/tests")


class GateError(RuntimeError):
    """A release gate condition is not satisfied."""


@dataclass(frozen=True)
class GateRequest:
    event: str
    version: str
    app_version: str
    commit_sha: str
    """For tag pushes this is GITHUB_SHA, confirmed against the peeled tag by run_gate."""


def resolve_request(env):
    """Derive the requested version and commit from the workflow event."""
    event = env.get("GITHUB_EVENT_NAME", "")
    try:
        if event == "push":
            ref = env.get("GITHUB_REF", "")
            version = env.get("GITHUB_REF_NAME", "")
            if ref != f"refs/tags/{version}":
                raise GateError(f"push ref {ref!r} is not the release tag refs/tags/{version}")
            app_version = require_version(version)
            commit_sha = require_commit_sha(env.get("GITHUB_SHA", ""))
        elif event == "workflow_dispatch":
            if env.get("GITHUB_REF") != f"refs/heads/{MAIN_BRANCH}":
                raise GateError(f"dry runs must be dispatched from {MAIN_BRANCH}, not {env.get('GITHUB_REF')!r}")
            version = env.get("INPUT_VERSION", "")
            app_version = require_version(version)
            commit_sha = require_commit_sha(env.get("INPUT_SHA", ""))
        else:
            raise GateError(f"unsupported event {event!r}")
    except ContractError as error:
        raise GateError(str(error)) from error
    return GateRequest(event, version, app_version, commit_sha)


def peel_tag(ref_doc, tag_doc, version):
    """Return (commit_sha, tag_object_sha) for an annotated release tag."""
    if not isinstance(ref_doc, dict) or ref_doc.get("ref") != f"refs/tags/{version}":
        raise GateError(f"tag ref refs/tags/{version} not found")
    target = ref_doc.get("object") or {}
    if target.get("type") != "tag":
        raise GateError(
            f"refs/tags/{version} points to a {target.get('type')!r}; release tags must be annotated"
        )
    if not isinstance(tag_doc, dict) or tag_doc.get("sha") != target.get("sha"):
        raise GateError(f"tag object for {version} does not match the tag ref")
    if tag_doc.get("tag") != version:
        raise GateError(f"tag object name {tag_doc.get('tag')!r} != {version}")
    peeled = tag_doc.get("object") or {}
    if peeled.get("type") != "commit":
        raise GateError(f"tag {version} must point directly to a commit, not {peeled.get('type')!r}")
    try:
        return require_commit_sha(peeled.get("sha")), require_commit_sha(tag_doc.get("sha"))
    except ContractError as error:
        raise GateError(str(error)) from error


def ancestry_on_main(returncode):
    """Interpret ``git merge-base --is-ancestor``: 0 yes, 1 no, other error."""
    if returncode == 0:
        return True
    if returncode == 1:
        raise GateError("commit is not in the history of origin/main")
    raise GateError(f"cannot determine main ancestry (git exit {returncode})")


def _repo_name(doc):
    return (doc or {}).get("full_name")


def select_ci_run(runs, commit_sha):
    """Select the latest Daily CI push run on main for the commit; it must have succeeded."""
    candidates = [
        run for run in runs
        if run.get("head_sha") == commit_sha
        and run.get("path") == CI_WORKFLOW_PATH
        and run.get("event") == "push"
        and run.get("head_branch") == MAIN_BRANCH
        and _repo_name(run.get("repository")) == REPOSITORY
        and _repo_name(run.get("head_repository")) == REPOSITORY
    ]
    if not candidates:
        raise GateError(f"no Daily CI push run on {MAIN_BRANCH} for {commit_sha}")
    run = max(candidates, key=lambda r: r["id"])
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise GateError(
            f"Daily CI run {run['id']} attempt {run.get('run_attempt')} is "
            f"{run.get('status')}/{run.get('conclusion')}, expected completed/success"
        )
    if type(run.get("run_attempt")) is not int or run["run_attempt"] < 1:
        raise GateError(f"Daily CI run {run['id']} has no valid run_attempt")
    return run


def _check_run_id(url):
    prefix = f"https://api.github.com/repos/{REPOSITORY}/check-runs/"
    if not isinstance(url, str) or not url.startswith(prefix) or not url[len(prefix):].isdigit():
        raise GateError(f"unexpected check_run_url {url!r}")
    return int(url[len(prefix):])


def verify_required_checks(run, jobs, check_runs, commit_sha):
    """Each required check must succeed in the selected run's latest attempt.

    The job of the latest attempt names its check run; that check run must be
    the newest one with that name in the run's check suite, come from GitHub
    Actions, and have succeeded. An older successful attempt never satisfies
    the gate when a newer attempt exists.
    """
    summary = {}
    for name in REQUIRED_CHECKS:
        named_jobs = [j for j in jobs if j.get("name") == name]
        if len(named_jobs) != 1:
            raise GateError(f"required check {name}: {len(named_jobs)} jobs in the latest attempt")
        job = named_jobs[0]
        if job.get("run_id") != run["id"] or job.get("run_attempt") != run["run_attempt"]:
            raise GateError(
                f"required check {name}: job belongs to run {job.get('run_id')} "
                f"attempt {job.get('run_attempt')}, not run {run['id']} attempt {run['run_attempt']}"
            )
        if job.get("head_sha") != commit_sha:
            raise GateError(f"required check {name}: job head_sha {job.get('head_sha')}")
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            raise GateError(f"required check {name}: job is {job.get('status')}/{job.get('conclusion')}")
        check_run_id = _check_run_id(job.get("check_run_url"))

        in_suite = [
            c for c in check_runs
            if c.get("name") == name
            and (c.get("check_suite") or {}).get("id") == run.get("check_suite_id")
        ]
        if not in_suite:
            raise GateError(f"required check {name}: no check run in check suite {run.get('check_suite_id')}")
        latest = max(in_suite, key=lambda c: c["id"])
        if latest["id"] != check_run_id:
            raise GateError(
                f"required check {name}: latest-attempt check run {check_run_id} "
                f"is not the newest in the suite ({latest['id']})"
            )
        app = latest.get("app") or {}
        if app.get("slug") != CHECK_APP_SLUG or app.get("id") != CHECK_APP_ID:
            raise GateError(f"required check {name}: produced by {app.get('slug')!r}, not GitHub Actions")
        if latest.get("head_sha") != commit_sha:
            raise GateError(f"required check {name}: check run head_sha {latest.get('head_sha')}")
        if latest.get("status") != "completed" or latest.get("conclusion") != "success":
            raise GateError(
                f"required check {name}: check run is {latest.get('status')}/{latest.get('conclusion')}"
            )
        summary[name] = {"check_run_id": latest["id"], "conclusion": latest["conclusion"]}
    return summary


def trim_run(run):
    keys = ("id", "name", "path", "event", "head_branch", "head_sha", "run_attempt",
            "status", "conclusion", "check_suite_id", "html_url", "created_at", "updated_at")
    trimmed = {k: run.get(k) for k in keys}
    trimmed["repository"] = _repo_name(run.get("repository"))
    trimmed["head_repository"] = _repo_name(run.get("head_repository"))
    return trimmed


def trim_job(job):
    keys = ("id", "name", "run_id", "run_attempt", "head_sha", "status", "conclusion",
            "check_run_url", "started_at", "completed_at")
    return {k: job.get(k) for k in keys}


def trim_check_run(check_run):
    keys = ("id", "name", "head_sha", "status", "conclusion", "details_url",
            "started_at", "completed_at")
    trimmed = {k: check_run.get(k) for k in keys}
    app = check_run.get("app") or {}
    trimmed["app_slug"] = app.get("slug")
    trimmed["app_id"] = app.get("id")
    trimmed["check_suite_id"] = (check_run.get("check_suite") or {}).get("id")
    return trimmed


def ghcr_evidence(states):
    conflicts = gate_conflicts(states)
    if conflicts:
        raise GateError(
            "GHCR already has release target tags: "
            + ", ".join(f"{s.repository}:{s.tag} ({s.digest})" for s in conflicts)
        )
    confirmed = all(s.state == NOT_FOUND for s in states)
    return {
        "query": "anonymous",
        "tags": [s.as_dict() for s in states],
        "absence_confirmed": confirmed,
        "note": (
            "All target tags confirmed absent by anonymous lookup."
            if confirmed else
            "UNKNOWN means the anonymous lookup could not determine the tag state "
            "(missing and private packages are indistinguishable). Absence is NOT "
            "confirmed here; build-push confirms it with an authenticated lookup "
            "before any image is pushed."
        ),
    }


def gate_summary(evidence):
    """The manifest ``gate`` group, derived from gate evidence."""
    run = evidence["daily_ci"]["workflow_run"]
    return {
        "daily_ci": {
            "run_id": run["id"],
            "run_attempt": run["run_attempt"],
            "event": run["event"],
            "head_branch": run["head_branch"],
            "conclusion": run["conclusion"],
        },
        "required_checks": {
            name: dict(value) for name, value in evidence["required_checks"].items()
        },
        "on_main": evidence["on_main"],
        "verified_at": evidence["captured_at"],
    }


def gate_evidence_errors(evidence):
    """Consistency checks for a gate-evidence document."""
    errors = []
    try:
        if evidence.get("schema_version") != GATE_EVIDENCE_SCHEMA_VERSION:
            errors.append("gate evidence: unsupported schema_version")
        if evidence.get("repository") != REPOSITORY:
            errors.append("gate evidence: repository mismatch")
        sha = evidence.get("commit_sha")
        run = evidence["daily_ci"]["workflow_run"]
        if (run.get("head_sha"), run.get("event"), run.get("head_branch"), run.get("conclusion")) != (
            sha, "push", MAIN_BRANCH, "success"
        ):
            errors.append("gate evidence: Daily CI run does not show a successful push on main for the SHA")
        if evidence.get("on_main") is not True:
            errors.append("gate evidence: on_main is not true")
        snapshot = {c.get("id"): c for c in evidence.get("check_runs", [])}
        required = evidence.get("required_checks", {})
        if set(required) != set(REQUIRED_CHECKS):
            errors.append("gate evidence: required_checks set mismatch")
        for name, value in required.items():
            check = snapshot.get(value.get("check_run_id"))
            if not check:
                errors.append(f"gate evidence: {name} check run missing from snapshot")
                continue
            if (check.get("name"), check.get("conclusion"), check.get("head_sha"),
                    check.get("app_slug"), check.get("check_suite_id")) != (
                    name, "success", sha, CHECK_APP_SLUG, run.get("check_suite_id")):
                errors.append(f"gate evidence: {name} snapshot does not match the summary")
            if value.get("conclusion") != "success":
                errors.append(f"gate evidence: {name} conclusion {value.get('conclusion')}")
        if any(t.get("state") == EXISTS for t in evidence["ghcr"]["tags"]):
            errors.append("gate evidence: GHCR conflict recorded")
        checks = evidence.get("delivery_checks") or []
        if not checks or any(c.get("result") != "passed" or c.get("source_sha") != sha for c in checks):
            errors.append("gate evidence: deterministic delivery checks did not pass on the SHA")
    except (KeyError, TypeError, AttributeError) as error:
        errors.append(f"gate evidence: malformed ({error!r})")
    return errors


@dataclass
class GateIO:
    """External effects used by run_gate (replaced by fakes in tests)."""
    github: object            # GitHubClient
    registry: object          # anonymous RegistryClient
    git: object               # callable(args) -> (returncode, stdout)
    run_tests: object         # callable(source_dir) -> returncode
    now: object               # callable() -> UTC timestamp string


def run_gate(env, io, source_dir):
    """Run every gate condition; return gate evidence or raise GateError."""
    request = resolve_request(env)
    if env.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise GateError(f"repository {env.get('GITHUB_REPOSITORY')!r} is not {REPOSITORY}")
    commit_sha = request.commit_sha
    tag_object_sha = None

    if request.event == "push":
        status, ref_doc = io.github.get_optional(f"git/ref/tags/{request.version}")
        if status != 200:
            raise GateError(f"tag {request.version} not found")
        target_sha = (ref_doc.get("object") or {}).get("sha")
        tag_doc = None
        if (ref_doc.get("object") or {}).get("type") == "tag":
            tag_doc = io.github.json("GET", f"git/tags/{target_sha}")
        commit_sha, tag_object_sha = peel_tag(ref_doc, tag_doc, request.version)
        returncode, local = io.git(["git", "rev-parse", "--verify", f"{request.commit_sha}^{{commit}}"])
        if returncode != 0 or local.strip() != commit_sha:
            raise GateError(
                f"GITHUB_SHA {request.commit_sha} does not resolve to the peeled tag commit {commit_sha}"
            )
        print(f"tag {request.version}: annotated object {tag_object_sha} -> commit {commit_sha}")

    returncode, _ = io.git(["git", "merge-base", "--is-ancestor", commit_sha, "refs/remotes/origin/main"])
    ancestry_on_main(returncode)
    print(f"commit {commit_sha} is in origin/{MAIN_BRANCH} history")

    runs = io.github.paginate(
        f"actions/workflows/ci.yml/runs?head_sha={commit_sha}&event=push&branch={MAIN_BRANCH}",
        key="workflow_runs",
    )
    run = select_ci_run(runs, commit_sha)
    jobs = io.github.paginate(f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs", key="jobs")
    check_runs = io.github.paginate(f"commits/{commit_sha}/check-runs?filter=all", key="check_runs")
    required = verify_required_checks(run, jobs, check_runs, commit_sha)
    print(f"Daily CI run {run['id']} attempt {run['run_attempt']}: required checks succeeded")

    status, _ = io.github.get_optional(f"releases/tags/{request.version}")
    if status != 404:
        raise GateError(f"a published release {request.version} already exists")
    print(f"no published release {request.version}")

    ghcr = ghcr_evidence(release_tag_states(io.registry, request.version, commit_sha))
    for tag in ghcr["tags"]:
        print(f"GHCR {tag['repository']}:{tag['tag']}: {tag['state']} ({tag['detail']})")
    if not ghcr["absence_confirmed"]:
        print("GHCR absence NOT confirmed anonymously; build-push must confirm it before pushing")

    returncode, _ = io.git(["git", "worktree", "add", "--detach", source_dir, commit_sha])
    if returncode != 0:
        raise GateError(f"cannot check out {commit_sha} for deterministic delivery checks")
    returncode, head = io.git(["git", "-C", source_dir, "rev-parse", "HEAD"])
    if returncode != 0 or head.strip() != commit_sha:
        raise GateError(f"delivery check source {source_dir} is not at {commit_sha}")
    if io.run_tests(source_dir) != 0:
        raise GateError("deterministic delivery checks failed on the exact SHA")

    return {
        "schema_version": GATE_EVIDENCE_SCHEMA_VERSION,
        "repository": REPOSITORY,
        "event": request.event,
        "tag": request.version,
        "app_version": request.app_version,
        "commit_sha": commit_sha,
        "tag_object_sha": tag_object_sha,
        "captured_at": io.now(),
        "gate_run": {
            "run_id": env.get("GITHUB_RUN_ID"),
            "run_attempt": env.get("GITHUB_RUN_ATTEMPT"),
            "workflow_ref": env.get("GITHUB_WORKFLOW_REF"),
        },
        "on_main": True,
        "daily_ci": {"workflow_run": trim_run(run), "jobs": [trim_job(j) for j in jobs]},
        "check_runs": [trim_check_run(c) for c in check_runs],
        "required_checks": required,
        "published_release": "absent",
        "ghcr": ghcr,
        "delivery_checks": [{
            "command": " ".join(DELIVERY_TEST_COMMAND),
            "source_sha": commit_sha,
            "result": "passed",
        }],
    }


def default_test_runner(source_dir):
    """Run the delivery tests at the exact SHA without credentials or dispatch inputs."""
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN" and not k.startswith("INPUT_")}
    return subprocess.run(list(DELIVERY_TEST_COMMAND), cwd=source_dir, env=env).returncode
