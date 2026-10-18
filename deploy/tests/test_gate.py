import unittest

from deploy.rag_delivery.gate import (
    GateError,
    GateIO,
    ancestry_on_main,
    gate_evidence_errors,
    peel_tag,
    resolve_request,
    run_gate,
    select_ci_run,
    verify_required_checks,
)
from deploy.rag_delivery.github import GitHubClient
from deploy.rag_delivery.registry import RegistryClient
from support import (
    CHECK_IDS,
    REPOSITORY,
    RUN_ID,
    SHA,
    SUITE_ID,
    TAG_OBJECT_SHA,
    VERSION,
    FakeGitHubTransport,
    FakePackage,
    FakeImage,
    FakeRegistry,
    SHA_TAG,
    all_check_runs,
    all_jobs,
    check_run,
    ci_run,
    dispatch_env,
    gate_evidence,
    gate_routes,
    quiet,
    job,
    push_env,
    repo_doc,
    tag_object_doc,
    tag_ref_doc,
)


class ResolveRequestTest(unittest.TestCase):
    def test_tag_push(self):
        request = resolve_request(push_env())
        self.assertEqual((request.event, request.version, request.app_version, request.commit_sha),
                         ("push", VERSION, "0.1.0", SHA))

    def test_dispatch_uses_inputs(self):
        request = resolve_request(dispatch_env())
        self.assertEqual((request.event, request.version, request.commit_sha), ("workflow_dispatch", VERSION, SHA))

    def test_rejections(self):
        cases = {
            "branch push": push_env(GITHUB_REF="refs/heads/main", GITHUB_REF_NAME="main"),
            "ref/name mismatch": push_env(GITHUB_REF="refs/tags/v9.9.9"),
            "invalid tag": push_env(GITHUB_REF="refs/tags/v1.0", GITHUB_REF_NAME="v1.0"),
            "pre-release tag": push_env(GITHUB_REF="refs/tags/v1.0.0-rc1", GITHUB_REF_NAME="v1.0.0-rc1"),
            "dispatch from feature branch": dispatch_env(GITHUB_REF="refs/heads/feature"),
            "dispatch from tag ref": dispatch_env(GITHUB_REF=f"refs/tags/{VERSION}"),
            "dispatch short sha": dispatch_env(INPUT_SHA=SHA[:7]),
            "dispatch upper sha": dispatch_env(INPUT_SHA=SHA.upper()),
            "dispatch non-hex sha": dispatch_env(INPUT_SHA="z" * 40),
            "dispatch empty sha": dispatch_env(INPUT_SHA=""),
            "dispatch bad version": dispatch_env(INPUT_VERSION="0.1.0"),
            "dispatch suffix version": dispatch_env(INPUT_VERSION="v0.1.0-dryrun"),
            "pull_request event": push_env(GITHUB_EVENT_NAME="pull_request"),
            "schedule event": push_env(GITHUB_EVENT_NAME="schedule"),
        }
        for name, env in cases.items():
            with self.subTest(name):
                with self.assertRaises(GateError):
                    resolve_request(env)


class PeelTagTest(unittest.TestCase):
    def test_annotated_tag_peels_to_commit(self):
        self.assertEqual(peel_tag(tag_ref_doc(), tag_object_doc(), VERSION), (SHA, TAG_OBJECT_SHA))

    def test_lightweight_tag_rejected(self):
        with self.assertRaisesRegex(GateError, "annotated"):
            peel_tag(tag_ref_doc(object_type="commit", sha=SHA), None, VERSION)

    def test_tag_of_tag_rejected(self):
        with self.assertRaises(GateError):
            peel_tag(tag_ref_doc(), tag_object_doc(object_type="tag"), VERSION)

    def test_mismatched_objects_rejected(self):
        with self.assertRaises(GateError):
            peel_tag(tag_ref_doc(), tag_object_doc(sha="f" * 40), VERSION)
        with self.assertRaises(GateError):
            peel_tag(tag_ref_doc(), tag_object_doc(version="v9.9.9"), VERSION)
        with self.assertRaises(GateError):
            peel_tag(tag_ref_doc(version="v9.9.9"), tag_object_doc(), VERSION)
        with self.assertRaises(GateError):
            peel_tag(tag_ref_doc(), tag_object_doc(commit=SHA[:39]), VERSION)


class AncestryTest(unittest.TestCase):
    def test_exit_codes(self):
        self.assertTrue(ancestry_on_main(0))
        with self.assertRaisesRegex(GateError, "not in the history"):
            ancestry_on_main(1)
        with self.assertRaisesRegex(GateError, "cannot determine"):
            ancestry_on_main(128)


class SelectCiRunTest(unittest.TestCase):
    def test_successful_push_run_on_main(self):
        self.assertEqual(select_ci_run([ci_run()], SHA)["id"], RUN_ID)

    def test_failed_or_unfinished_run_rejected(self):
        for overrides in ({"conclusion": "failure"}, {"conclusion": "cancelled"},
                          {"status": "in_progress", "conclusion": None}, {"conclusion": "skipped"}):
            with self.subTest(overrides):
                with self.assertRaises(GateError):
                    select_ci_run([ci_run(**overrides)], SHA)

    def test_wrong_run_identity_rejected(self):
        for overrides in ({"event": "pull_request"}, {"event": "workflow_dispatch"},
                          {"head_branch": "feature"}, {"head_sha": "f" * 40},
                          {"path": ".github/workflows/backend-image.yml"},
                          {"head_repository": repo_doc("someone/fork")},
                          {"repository": repo_doc("someone/fork")}):
            with self.subTest(overrides):
                with self.assertRaisesRegex(GateError, "no Daily CI push run"):
                    select_ci_run([ci_run(**overrides)], SHA)

    def test_no_runs(self):
        with self.assertRaises(GateError):
            select_ci_run([], SHA)

    def test_latest_run_decides(self):
        older_ok = ci_run(id=RUN_ID - 5)
        newer_failed = ci_run(conclusion="failure")
        with self.assertRaises(GateError):
            select_ci_run([older_ok, newer_failed], SHA)
        older_failed = ci_run(id=RUN_ID - 5, conclusion="failure")
        self.assertEqual(select_ci_run([older_failed, ci_run()], SHA)["id"], RUN_ID)

    def test_latest_attempt_conclusion_decides(self):
        # The runs API reports the latest attempt; a failed rerun overrides an earlier success.
        with self.assertRaises(GateError):
            select_ci_run([ci_run(run_attempt=2, conclusion="failure")], SHA)
        self.assertEqual(select_ci_run([ci_run(run_attempt=2)], SHA)["run_attempt"], 2)


class RequiredChecksTest(unittest.TestCase):
    def test_all_required_checks_pass(self):
        summary = verify_required_checks(ci_run(), all_jobs(), all_check_runs(), SHA)
        self.assertEqual(summary["backend-contracts"],
                         {"check_run_id": CHECK_IDS["backend-contracts"], "conclusion": "success"})
        self.assertEqual(len(summary), 4)

    def test_missing_check(self):
        for name in CHECK_IDS:
            with self.subTest(name):
                jobs = [j for j in all_jobs() if j["name"] != name]
                with self.assertRaisesRegex(GateError, name):
                    verify_required_checks(ci_run(), jobs, all_check_runs(), SHA)
                runs = [c for c in all_check_runs() if c["name"] != name]
                with self.assertRaisesRegex(GateError, name):
                    verify_required_checks(ci_run(), all_jobs(), runs, SHA)

    def test_failed_check(self):
        checks = all_check_runs()
        checks[2]["conclusion"] = "failure"
        with self.assertRaises(GateError):
            verify_required_checks(ci_run(), all_jobs(), checks, SHA)
        jobs = all_jobs()
        jobs[0]["conclusion"] = "failure"
        with self.assertRaises(GateError):
            verify_required_checks(ci_run(), jobs, all_check_runs(), SHA)

    def test_wrong_check_source(self):
        for app in ({"slug": "some-other-app", "id": 999}, {"slug": "github-actions", "id": 1}, {}):
            with self.subTest(app=app):
                checks = all_check_runs()
                checks[0]["app"] = app
                with self.assertRaisesRegex(GateError, "GitHub Actions"):
                    verify_required_checks(ci_run(), all_jobs(), checks, SHA)

    def test_check_run_from_other_suite_rejected(self):
        checks = all_check_runs()
        checks[1]["check_suite"] = {"id": SUITE_ID + 1}
        with self.assertRaisesRegex(GateError, "check suite"):
            verify_required_checks(ci_run(), all_jobs(), checks, SHA)

    def test_job_from_other_run_or_attempt_rejected(self):
        for overrides in ({"run_id": RUN_ID + 1}, {"run_attempt": 2}, {"head_sha": "f" * 40}):
            with self.subTest(overrides):
                jobs = all_jobs()
                jobs[3].update(overrides)
                with self.assertRaises(GateError):
                    verify_required_checks(ci_run(), jobs, all_check_runs(), SHA)

    def test_duplicate_job_names_rejected(self):
        jobs = all_jobs() + [job("compose-config")]
        with self.assertRaisesRegex(GateError, "2 jobs"):
            verify_required_checks(ci_run(), jobs, all_check_runs(), SHA)

    def test_unexpected_check_run_url_rejected(self):
        jobs = all_jobs()
        jobs[0]["check_run_url"] = "https://api.github.com/repos/someone/fork/check-runs/1"
        with self.assertRaisesRegex(GateError, "check_run_url"):
            verify_required_checks(ci_run(), jobs, all_check_runs(), SHA)

    def test_latest_attempt_overrides_older_failure(self):
        run = ci_run(run_attempt=2)
        new_id = CHECK_IDS["frontend-image"] + 1000
        checks = all_check_runs()
        checks[2]["conclusion"] = "failure"  # attempt 1 failed
        checks.append(check_run("frontend-image", check_id=new_id))  # attempt 2 succeeded
        jobs = [job(n, run_attempt=2, check_id=(new_id if n == "frontend-image" else None)) for n in CHECK_IDS]
        summary = verify_required_checks(run, jobs, checks, SHA)
        self.assertEqual(summary["frontend-image"]["check_run_id"], new_id)

    def test_latest_attempt_failure_overrides_older_success(self):
        run = ci_run(run_attempt=2)
        new_id = CHECK_IDS["frontend-image"] + 1000
        checks = all_check_runs() + [check_run("frontend-image", check_id=new_id, conclusion="failure")]
        jobs = [job(n, run_attempt=2, check_id=(new_id if n == "frontend-image" else None)) for n in CHECK_IDS]
        jobs[2]["conclusion"] = "failure"
        with self.assertRaises(GateError):
            verify_required_checks(run, jobs, checks, SHA)
        # Even if the job record claimed success, the newer failed check run decides.
        jobs[2]["conclusion"] = "success"
        with self.assertRaises(GateError):
            verify_required_checks(run, jobs, checks, SHA)

    def test_stale_attempt_check_run_rejected(self):
        # The job points at an older check run although a newer one exists in the suite.
        checks = all_check_runs() + [check_run("compose-config", check_id=CHECK_IDS["compose-config"] + 1000)]
        with self.assertRaisesRegex(GateError, "not the newest"):
            verify_required_checks(ci_run(), all_jobs(), checks, SHA)


def gate_io(routes=None, registry=None, ancestry=0, head=SHA, tests=0, calls=None, worktree=0):
    calls = calls if calls is not None else []

    def git(args):
        calls.append(("git", args))
        if args[1] == "merge-base":
            return ancestry, ""
        if args[1] == "worktree":
            return worktree, ""
        if args[1:3] == ["rev-parse", "--verify"]:
            # Local peel of GITHUB_SHA: the commit itself or the annotated tag object.
            return (0, SHA + "\n") if args[3] in (f"{SHA}^{{commit}}", f"{TAG_OBJECT_SHA}^{{commit}}") else (128, "")
        return 0, head + "\n"

    def run_tests(source_dir):
        calls.append(("tests", source_dir))
        return tests

    return GateIO(
        github=GitHubClient("token", REPOSITORY, FakeGitHubTransport(routes or gate_routes())),
        registry=RegistryClient(registry or FakeRegistry()),
        git=git, run_tests=run_tests, now=lambda: "2026-10-19T08:00:00Z",
    )


class RunGateTest(unittest.TestCase):
    def test_tag_push_passes_and_records_unknown_ghcr_state(self):
        calls = []
        evidence = quiet(run_gate, push_env(), gate_io(calls=calls), "/src")
        self.assertEqual((evidence["tag"], evidence["commit_sha"], evidence["tag_object_sha"]),
                         (VERSION, SHA, TAG_OBJECT_SHA))
        self.assertEqual(gate_evidence_errors(evidence), [])
        # Missing packages are DENIED anonymously: UNKNOWN, recorded, never "absent".
        self.assertEqual({t["state"] for t in evidence["ghcr"]["tags"]}, {"UNKNOWN"})
        self.assertFalse(evidence["ghcr"]["absence_confirmed"])
        self.assertIn("NOT confirmed", evidence["ghcr"]["note"])
        self.assertEqual(calls[-1], ("tests", "/src"))

    def test_dispatch_passes_without_tag(self):
        evidence = quiet(run_gate, dispatch_env(), gate_io(), "/src")
        self.assertIsNone(evidence["tag_object_sha"])
        self.assertEqual(evidence["event"], "workflow_dispatch")

    def test_public_package_absent_tags_are_confirmed_not_found(self):
        packages = {FakeRegistry.name(s): FakePackage(public=True) for s in ("backend", "frontend")}
        for package, service in zip(packages.values(), ("backend", "frontend")):
            package.put(FakeImage(service), ["sha-0000000", "v0.0.9"])
        evidence = quiet(run_gate, push_env(), gate_io(registry=FakeRegistry(packages)), "/src")
        self.assertEqual({t["state"] for t in evidence["ghcr"]["tags"]}, {"NOT_FOUND"})
        self.assertTrue(evidence["ghcr"]["absence_confirmed"])

    def test_existing_public_tag_fails(self):
        package = FakePackage(public=True)
        package.put(FakeImage("backend"), [SHA_TAG])
        registry = FakeRegistry({FakeRegistry.name("backend"): package})
        with self.assertRaisesRegex(GateError, "already has release target tags"):
            quiet(run_gate, push_env(), gate_io(registry=registry), "/src")

    def test_failures_stop_before_tests(self):
        cases = {
            "not on main": dict(ancestry=1),
            "ancestry unknown": dict(ancestry=128),
            "ci failed": dict(routes=gate_routes(runs=[ci_run(conclusion="failure")])),
            "pr run only": dict(routes=gate_routes(runs=[ci_run(event="pull_request")])),
            "check missing": dict(routes=gate_routes(jobs=all_jobs()[:3])),
            "published release": dict(routes=gate_routes(release_status=200)),
            "lightweight tag": dict(routes=gate_routes(tag_ref=tag_ref_doc(object_type="commit", sha=SHA))),
            "tag peels elsewhere": dict(routes=gate_routes(tag_obj=tag_object_doc(commit="f" * 40))),
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                calls = []
                with self.assertRaises(GateError):
                    quiet(run_gate, push_env(), gate_io(calls=calls, **kwargs), "/src")
                self.assertNotIn("tests", [c[0] for c in calls])

    def test_exact_sha_worktree_is_created_after_checks(self):
        calls = []
        quiet(run_gate, push_env(), gate_io(calls=calls), "/src")
        git_calls = [c[1][1] for c in calls if c[0] == "git"]
        self.assertEqual(git_calls, ["rev-parse", "merge-base", "worktree", "-C"])
        worktree = [c[1] for c in calls if c[0] == "git" and c[1][1] == "worktree"][0]
        self.assertEqual(worktree, ["git", "worktree", "add", "--detach", "/src", SHA])

    def test_source_checkout_and_tests_must_match(self):
        with self.assertRaisesRegex(GateError, "cannot check out"):
            quiet(run_gate, push_env(), gate_io(worktree=128), "/src")
        with self.assertRaisesRegex(GateError, "not at"):
            quiet(run_gate, push_env(), gate_io(head="f" * 40), "/src")
        with self.assertRaisesRegex(GateError, "deterministic delivery checks failed"):
            quiet(run_gate, push_env(), gate_io(tests=1), "/src")

    def test_wrong_repository_rejected(self):
        with self.assertRaisesRegex(GateError, "repository"):
            quiet(run_gate, push_env(GITHUB_REPOSITORY="someone/fork"), gate_io(), "/src")

    def test_tag_commit_must_match_github_sha(self):
        with self.assertRaisesRegex(GateError, "GITHUB_SHA"):
            quiet(run_gate, push_env(GITHUB_SHA="f" * 40), gate_io(), "/src")
        # GITHUB_SHA naming the annotated tag object peels to the same commit.
        evidence = quiet(run_gate, push_env(GITHUB_SHA=TAG_OBJECT_SHA), gate_io(), "/src")
        self.assertEqual(evidence["commit_sha"], SHA)


class GateEvidenceTest(unittest.TestCase):
    def test_fixture_is_consistent(self):
        self.assertEqual(gate_evidence_errors(gate_evidence()), [])

    def test_inconsistent_evidence_detected(self):
        evidence = gate_evidence()
        evidence["required_checks"]["frontend-image"]["check_run_id"] = 1
        self.assertTrue(gate_evidence_errors(evidence))
        evidence = gate_evidence(on_main=False)
        self.assertTrue(gate_evidence_errors(evidence))
        evidence = gate_evidence(delivery_checks=[])
        self.assertTrue(gate_evidence_errors(evidence))
        evidence = gate_evidence()
        evidence["ghcr"]["tags"][0]["state"] = "EXISTS"
        self.assertTrue(gate_evidence_errors(evidence))
        evidence = gate_evidence()
        del evidence["daily_ci"]
        self.assertTrue(gate_evidence_errors(evidence))


if __name__ == "__main__":
    unittest.main()
