# Phase E — Continuous delivery contract

This local-first engineering baseline is **production-oriented, but not
production-ready**. Phase E adds Continuous Delivery: an immutable,
traceable release that a human approves and deploys into an isolated local
Compose project. It is not Continuous Deployment. No release is deployed
automatically, and deploying the real project or real `rag_data` volume is
outside Phase E.

This is the initial CD-WP1 contract. It defines release identity, the release
manifest, release completeness, exact-SHA semantics, distribution and
licensing boundaries, and the approval order that later work packages
implement. It is not the final operations guide: workflows, deployment
commands and acceptance evidence are added by later work packages, and CD-WP7
completes this document.

## Status at CD-WP1

Verified read-only on 2026-10-18 against `main` at
`57db7d4ebceb0d423f59b6a0a417a610c55dd541`:

| Item | State |
| --- | --- |
| Git tags / GitHub Releases / Environments | 0 / 0 / 0 |
| Rulesets | Only `main-pr-quality-gate` (branch `refs/heads/main`, four required checks, no bypass actors) |
| Immutable Releases | Disabled |
| Repository license | No `LICENSE` file; GitHub reports `license: null` |
| Release workflow, deployment tooling | Not present |
| Version literals | `Backend/__init__.py`, `Backend/routes/health.py` and `Frontend/package.json` all contain `1.0.0`; none is a release identity |

Nothing described below exists as executable behavior until the work package
that owns it is merged. Where this document and a later workflow or validator
disagree, the discrepancy is a defect to resolve, not a silent override.

## Release identity

```text
git tag vX.Y.Z (annotated, protected by tag rulesets)
  └─ peel ─► commit SHA (40 hex): ancestor of origin/main, Daily CI push run on main succeeded
        ├─► ghcr.io/henric0612/rag-news-backend  :vX.Y.Z, :sha-<7> ─► digest Db
        ├─► ghcr.io/henric0612/rag-news-frontend :vX.Y.Z, :sha-<7> ─► digest Df
        └─► GitHub Release vX.Y.Z (published, immutable)
               assets: release-manifest.json, gate-evidence.json, SHA256SUMS
```

- **The Git tag is the only release version source.** The repository keeps no
  version file and release work does not create version-bump commits.
- **Version format.** Tags must match
  `^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`. Pre-release and
  build-metadata suffixes are not used in Phase E. The first release is
  `v0.1.0`; the `0.x` major version states that the project is not
  production-ready. Any release-level correction increments the patch number.
- **A published version number is never reused.** Tags matching `v*` are
  never moved or deleted, and the same version is never republished. Deleting
  a release requires explicit approval and retires its tag name permanently.
- **Identity mapping.** `APP_VERSION` is the tag without the leading `v`
  (`v0.1.0` → `0.1.0`). `GIT_SHA` is the full 40-character commit SHA
  obtained by peeling the tag. Each image is identified by its registry
  digest.
- **The digest is authoritative.** `:vX.Y.Z` and `:sha-<7>` are mutable
  registry aliases. Every deployment and rollback references images as
  `name@sha256:<digest>`; a tag reference is never a deployment identity.
- **Release builds versus local builds.** Release builds inject
  `APP_VERSION` and `GIT_SHA` as build arguments. Local builds, including
  `docker compose build`, receive no release identity and report
  `0.0.0-dev` / `unknown` once CD-WP2 introduces runtime build information.
  A local build is never a release, whatever its source commit.
- **npm metadata.** `Frontend/package.json` `version` is npm package metadata,
  not release identity, and is not updated per release. The Backend `1.0.0`
  literals are replaced by runtime build information in CD-WP2.

## GHCR distribution

Image names, derived from the repository owner `Henric0612`, use the
lowercase namespace required by image references:

| Image | Repository | Tags per release |
| --- | --- | --- |
| Backend | `ghcr.io/henric0612/rag-news-backend` | `vX.Y.Z`, `sha-<first 7 SHA characters>` |
| Frontend | `ghcr.io/henric0612/rag-news-frontend` | `vX.Y.Z`, `sha-<first 7 SHA characters>` |

Both images target `linux/amd64` only. From CD-WP2, release images carry the
`org.opencontainers.image.source` label so GHCR links each package to this
repository.

GitHub documentation verified on 2026-10-18:

| Topic | Documented behavior | Source |
| --- | --- | --- |
| Visibility | "When you first publish a package, the default visibility is private." | [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) |
| Repository linking | `org.opencontainers.image.source` associates a package with a repository; a linked package inherits that repository's access permissions | Same page |
| `GITHUB_TOKEN` | Can publish packages associated with the workflow repository, but may lack push permission if the namespace was previously pushed without that association | Same page |
| Layer size | 10 GB limit per layer | Same page |
| Cost | "GitHub Packages usage is free for public packages." "Container image storage and bandwidth for the Container registry is currently free"; Container registry users are informed at least one month before a policy change | [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages) |

Cost policy: images are pushed only by release tags, and released packages
are public; no per-commit images are published. A pricing-policy change that makes distribution non-free stops
release work for Human Review; no automatic fallback is configured.

Whether a package with the same name already exists in the namespace is not
yet verified: the local GitHub CLI token lacks `read:packages`. Before R1 the
owner either grants that scope for a read-only check or accepts that the first
release run will expose a conflict by failing.

### First public release boundary

The first release is fail-closed. Because GHCR creates new packages as
private, the first tag run is expected to push private images and then fail the
anonymous-pull check in the release job **before any Release object is
created**. The expected residue is exactly: private images, the protected tag,
and a failed workflow run. There is no draft and no release, so that version
is not deployable.

The owner then pulls the exact digests while logged in and reviews the image
filesystem, labels, license inventory and package-to-repository link. Making
the packages public is a separate approval (P1). Only afterwards is the same
run resumed with **Re-run failed jobs**: the release job resolves the
already-pushed digests from the registry, without building or pushing, and
completes the release. If the review fails, the packages are not made public
and the version number is retired under Human Review. Later releases, with
public packages, complete in a single run. Re-running is possible only within
GitHub's re-run window, expected to be 30 days after the initial run and not
yet verified (U4).

## Release manifest

Each release publishes `release-manifest.json` with `schema_version: 1`. All
values are produced by the release workflow from the sources listed; nothing
is written by hand.

| Group | Fields | Meaning | Source |
| --- | --- | --- | --- |
| Identity | `schema_version` (`1`), `kind` (always `release`), `project`, `repository`, `tag`, `app_version`, `commit_sha`, `tag_object_sha` | Release identity; `commit_sha` is the peeled tag commit, `tag_object_sha` the annotated tag object | Gate job |
| Gate | `gate.daily_ci.{run_id, run_attempt, event, head_branch, conclusion}`; `gate.required_checks.<check>.{check_run_id, conclusion}` for `backend-contracts`, `frontend-contracts`, `frontend-image`, `compose-config`; `gate.on_main`; `gate.verified_at` | Evidence that the SHA passed required CI on `main` at release time: `event` is `push`, `head_branch` is `main`, `on_main` is `true` | GitHub API, at gate time |
| Build | `build.{release_run_id, run_attempt, workflow_ref, runner, docker_version, built_at}` | Which workflow run built and published the images | Actions context |
| Images | `images.{backend,frontend}.{repository, digest, ref, tags[], platform, media_type, compressed_size_bytes, uncompressed_size_bytes, max_layer_bytes}` | Registry identity; `ref` is `repository@digest`, `tags` holds `vX.Y.Z` and `sha-<7>`, `platform` is `linux/amd64` | Registry read-back after push |
| Inputs | `inputs.base_images` (resolved digests of `python:3.13-slim`, `node:24-alpine`, `caddy:2-alpine`); `inputs.models` (embedding and reranker id plus revision, from the `Backend/Dockerfile` build arguments); `inputs.files` (sha256 of `Backend/Dockerfile`, `Frontend/Dockerfile`, `Backend/requirements.lock`, `Frontend/package-lock.json`, `Frontend/Caddyfile`) | Build inputs that affect image contents | Build job |
| Data compatibility | `data_compat.declared_schema_fingerprint`; `data_compat.embedding` (model plus revision); `data_compat.data_format_version` (`1`) | Compatibility key for rollback and restore decisions | Build job |
| External | `external.llm_model` (`qwen3:8b`) | Host-provided Ollama model; not bundled in any image | Constant |

`declared_schema_fingerprint` is the sha256 of the DDL produced by compiling
the image's SQLAlchemy metadata with the SQLite dialect, ordered by table
name. It describes the schema the version **declares**. It is compared only
with the same field of another manifest, never with a fingerprint observed on
a data volume; those two fingerprints use different normalized inputs and
their equivalence is unproven.

The current pinned models are `sentence-transformers/all-MiniLM-L6-v2` and
`cross-encoder/ms-marco-MiniLM-L-6-v2`, with revisions set by the
`EMBEDDING_REVISION` and `RERANK_REVISION` arguments in
[`Backend/Dockerfile`](../Backend/Dockerfile).

### Companion assets

| Asset | Responsibility |
| --- | --- |
| `gate-evidence.json` | Raw snapshot of the check-runs API response taken by the gate, with unrelated fields removed. It keeps the CI evidence available after Actions log retention expires. The manifest's `gate.required_checks` summary is derived from this snapshot. |
| `SHA256SUMS` | sha256 checksums of `release-manifest.json` and `gate-evidence.json`. |

Verification order: verify `SHA256SUMS` first; trust neither JSON file unless
its checksum matches; then validate the manifest. Immutable Releases protect
the published assets from modification.

### Validator contract

The executable validator is delivered in CD-WP3 and becomes the authoritative
executable form of this contract; CD-WP1 adds no schema file or tool. The
validator must reject a manifest unless:

- `kind` is `release` and `schema_version` is `1`;
- every field in the manifest table above is present with its expected type;
- `tag` matches the version pattern and `app_version` equals `tag` without
  `v`;
- `commit_sha` is 40 lowercase hexadecimal characters;
- each `digest` is a well-formed `sha256:` digest and `ref` equals
  `repository@digest`;
- `tags` contains both `vX.Y.Z` and `sha-<7>`, and `sha-<7>` equals the first
  seven characters of `commit_sha`.

Rehearsal manifests used before the first release have a separate
`kind: rehearsal` structure without gate or registry fields. The release
validator always rejects them, and they are never release evidence.

## Release completeness

A version is **COMPLETE** if and only if all five conditions hold:

1. The GitHub Release exists with `draft=false` and, once Immutable Releases
   is enabled, `immutable=true`.
2. The release has all three assets, `SHA256SUMS` verifies, and the manifest
   validates.
3. The peeled tag SHA equals `manifest.commit_sha`.
4. Both `repository@digest` references can be pulled anonymously, and both
   `:vX.Y.Z` and `:sha-<7>` resolve to that digest.
5. The image `version` and `revision` labels match the manifest.

The release job checks conditions 2–5 before publishing. The release-mode
deployment tool checks all five again during preflight. A version that fails
any condition is **INCOMPLETE** and must not be deployed.

These states are never deployable releases:

- a draft GitHub Release, including a draft left by a failed run;
- images in GHCR without a published release (orphaned images, such as the
  private images left by the first-release fail-closed path);
- a partial publication, such as only one image or only one tag;
- a locally built image or rehearsal manifest.

A partial publication that cannot be resumed with **Re-run failed jobs** goes
to Human Review. Deleting orphaned package versions requires its own
approval; the version number is retired and the fix is released as the next
patch version.

## Exact-SHA semantics

- **Release-level durable evidence** is the published release manifest and
  gate evidence (immutable assets), the GitHub release attestation and the
  locked tag. Together they show that the release artifacts came from that
  SHA, and that the SHA passed required CI at release time.
- **Later `main` commits do not invalidate a published release.** Its
  evidence describes its own SHA, not the current branch head.
- **Every new release reruns the full gate** on its exact SHA. No evidence is
  inherited from an earlier release, a pull request run or a dry run.
- **Phase E acceptance is separate from release validity.** It binds to the
  final `main` SHA, which is the `v0.1.1` commit. That SHA must have Daily CI
  with all four required checks successful and Backend Image Validation
  successful, `v0.1.1` must be COMPLETE, and the isolated release-mode
  N → N+1 → N run with at least one data restore (L4) must pass. Rehearsal-mode
  runs before the first release never count as acceptance evidence. Any later commit to `main` means the "Phase E accepted"
  conclusion must be reestablished; it does not affect published releases.
- **Identity changes** are never made by moving or deleting tags or by
  republishing a version. Any correction is a new patch version.

## Licensing and redistribution

The repository has no `LICENSE` file. Public images therefore contain project
code in the same "no license granted" state as the public source repository.
This does not block the owner from distributing the images. Whether to add a
license is an owner decision (H3) outside Phase E scope; Phase E adds no license and writes no `org.opencontainers.image.licenses`
label.

Third-party redistribution in public images (U10) is **not yet concluded**.
CD-WP1 defines the method only. The inventory is produced read-only from the
images built by the D1 dry run (after CD-WP4 is merged), and the release images
are checked again before P1:

| Component | Method |
| --- | --- |
| Debian packages | In the Backend image (`python:3.13-slim`, Debian-based): `dpkg-query -W -f '${Package} ${Version}\n'`, plus the presence of `/usr/share/doc/<package>/copyright` for every listed package; missing copyright files are recorded as findings |
| Alpine packages | The Frontend runtime image (`caddy:2-alpine`) has no `dpkg`. Its packages are listed read-only with `apk list --installed`, which reports each package's declared license |
| Python distributions | In the Backend image: read every installed distribution with `importlib.metadata` and record name, version, `License` (and `License-Expression` where present) and `License ::` classifiers |
| npm dependencies | At the inventoried SHA (the D1 SHA, then the release SHA before P1): `npm ls --all --json` in `Frontend/`, cross-referenced with the `license` fields in `Frontend/package-lock.json`, recording whether each package is dev-only. The runtime image contains only the bundled build output, so this inventory covers what is bundled into it |
| Caddy and other non-package binaries | Confirm the Caddy binary license (expected Apache-2.0, unverified) from official Caddy sources and the official image metadata. Record other components installed outside the package manager, such as the CPython interpreter in the Python base image, from their official upstream license sources |
| Models | The Hugging Face model API reported `apache-2.0` for `sentence-transformers/all-MiniLM-L6-v2` and `cross-encoder/ms-marco-MiniLM-L6-v2` (checked 2026-10-18). The pinned reranker id is `cross-encoder/ms-marco-MiniLM-L-6-v2`; reconfirm both licenses for the exact pinned ids and revisions |

Review and escalation:

- Every copyleft license (for example GPL, LGPL, AGPL or MPL), unknown or
  missing license, missing Debian copyright file, or license that may restrict
  redistribution is listed. Release work stops for Human Review of each item.
  Debian-based images normally contain GPL-licensed packages, so this review is
  expected, not exceptional.
- R1 and P1 stay blocked until the review records no blocking item.
- The raw inventory is retained outside Git with the Phase E evidence. A later
  documentation change records the conclusion here.

## Repository protection settings (G1)

G1 is a separate approval, executed only after this document is merged. It
changes repository settings, not repository files. `main-pr-quality-gate` and
its four required checks remain unchanged.

| Setting | Expected configuration | Purpose |
| --- | --- | --- |
| Ruleset `release-tags-immutable` | Target `tag`; include `refs/tags/v*`; rules `update`, `deletion`, `non_fast_forward`; enforcement active; **no bypass actors** | No one can move or delete a release tag |
| Ruleset `release-tags-create` | Target `tag`; include `refs/tags/v*`; rule `creation`; enforcement active; bypass actor: Repository admin role | Only the repository admin can create release tags |
| Immutable Releases | Enabled | Published releases lock their tag and assets and gain a release attestation |

The three layers are independent: tag rulesets prevent drift before and after
publication, and Immutable Releases lock the published release itself.

Evidence: after G1, read the settings back with
`gh api repos/Henric0612/rag-news-intelligence-platform/rulesets`, each new
ruleset by ID, and
`gh api repos/Henric0612/rag-news-intelligence-platform/immutable-releases`.
Keep the output outside Git.

| Gap | Assumption | Closure |
| --- | --- | --- |
| U5 | A personal repository ruleset accepts the Repository admin role as a bypass actor | Closed only when the read-back of `release-tags-create` shows that bypass actor. GitHub's guide to creating repository rulesets (checked 2026-10-18) lists Repository admins as eligible for bypass but does not address personal (user-owned) repositories specifically |
| U6 | Immutable Releases is enabled and governs releases published after enabling | Closed when the read-back shows `enabled: true` before any release. Each release's `immutable` field is then checked as COMPLETE condition 1 |

If the API, permissions or ruleset features differ from this table, G1 stops
for Human Review. No substitute protection is applied. Reverting G1 (deleting
a ruleset or disabling Immutable Releases) requires the same approval level.

Until G1 is verified and D1 is complete, no `v*` tag is created.

## Approval matrix and order

Each work package is delivered through its own pull request under
`main-pr-quality-gate`. Each approval point below is granted separately;
approving the E1 plan or an earlier step authorizes none of them.

| Approval | Scope | Precondition |
| --- | --- | --- |
| A1 | CD-WP1: this document (branch, commit, pull request) | E1 accepted |
| A2–A7 | CD-WP2–CD-WP7 implementation (branch, commit, pull request) | Previous work package merged |
| G1 | Tag rulesets and Immutable Releases | CD-WP1 document merged |
| D1 | Manual `workflow_dispatch` dry runs that write nothing, including the candidate-SHA dry run before R1 and before R2 | CD-WP4 merged and its contract tests passing, so the gate contains all approved deterministic delivery checks |
| L1–L4 | Local isolated Docker work: L1 Compose no-rebuild negative test, L2 rehearsal deployment, L3 rehearsal rollback and restore, L4 final N → N+1 → N with restore | Corresponding pull request merged or branch reviewed |
| R1 / R2 | Push `v0.1.0` / `v0.1.1`: create the tag, push to GHCR, create the GitHub Release | G1, D1 and L3 complete; positive dry run on the candidate SHA; the four required checks successful on that SHA; D1 image-content review and license inventory with no blocking item; L2/L3 rehearsal records passing |
| P1 | Make the GHCR packages public | Logged-in pull and manual review of this release's digests: filesystem, labels, license inventory; packages linked to the repository |
| Not in Phase E | Deploying the real project or real `rag_data` volume | Separate future approval |

```text
A1 CD-WP1 ─► PR (this document) ─► G1 settings
 └─ A2 CD-WP2 ─► A3 CD-WP3 ─► A4 CD-WP4 ─► L1 ─► D1 dry runs (complete gate)
    └─ A5 CD-WP5 ─► L2 ─► A6 CD-WP6 ─► L3
       └─ A7 CD-WP7: candidate dry run ─► R1 v0.1.0 ─► content review ─► P1 ─► re-run failed jobs
          ─► documentation PR ─► Backend Image Validation on final SHA ─► candidate dry run
          ─► R2 v0.1.1 ─► L4 ─► final acceptance
```

## Deferred items

Recorded, not implemented in Phase E: base-image digest pinning; image
signing, SBOMs and supply-chain hardening beyond the platform's release
attestation; multi-architecture images; making `delivery-contracts` a
required check (H4); a repository license (H3); automated GHCR retention;
real-project deployment; a schema migration framework; a Frontend runtime
version endpoint; browser end-to-end tests; historical observability export.
