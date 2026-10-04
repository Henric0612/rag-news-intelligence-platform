# Phase C — CI-tested AI application

Phase C adds repeatable software checks and a protected pull-request path to the local-first containerized RAG system. The project remains **production-oriented, but not production-ready**. CI proves selected software and build contracts; real AI behavior requires separate local validation.

## Scope and workflows

| Workflow | Trigger | Responsibility |
| --- | --- | --- |
| [Daily CI](../.github/workflows/ci.yml) | PR to `main`, push to `main`, manual | `backend-contracts`, `frontend-contracts`, `frontend-image`, `compose-config` |
| [Backend Image Validation](../.github/workflows/backend-image.yml) | Manual | `backend-image`: full Backend image build without layer cache |

The daily checks have no path filter. They use committed dependency locks, generate test reports, build the Frontend production bundle and image, and parse Compose configuration without starting services. The Backend image workflow is a separate, on-demand acceptance check because its model provisioning makes a full build expensive.

## Backend CI contract

`backend-contracts` runs on Ubuntu 24.04 with Python 3.13. `Backend/requirements.txt` declares dependencies; `Backend/requirements.lock` pins the CI installation. The job checks dependency consistency and imports key packages without loading models, then runs from the repository root:

```bash
python -m pytest -c Backend/pytest.ini Backend/tests -m ci \
  --cov=Backend --cov-config=Backend/tests/.coveragerc \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/backend-coverage.xml \
  --junitxml=artifacts/backend-junit.xml
```

The `ci` marker selects the approved deterministic 41-case inventory: environment (6), models (3), authentication service (4), authentication API (12), health/readiness API (7), authentication integration (2), RAG failure contract (5), and vector mapping regression (2). The marked tests and workflow are the executable contract. Other pytest modules remain local test assets. CI uses temporary SQLite and mocked AI dependencies; it does not need a running Ollama, GPU, real model cache, or user database.

## Frontend CI contract

`frontend-contracts` runs on Ubuntu 24.04 with Node 24 and `npm ci` from `Frontend/package-lock.json`. Its authoritative test command is:

```bash
cd Frontend
npm run test:ci
npm run build
```

`test:ci` selects all intended Unit and Integration Vitest modules, including the API URL regression. Unhandled errors and Promise rejections fail the run. It removes stale reports before execution, requires nonempty JUnit XML (`coverage/junit.xml`) and LCOV (`coverage/lcov.info`), and prints a coverage summary. Security, performance, and Playwright Browser E2E assets are outside this required contract.

## Coverage and build strategy

Backend and Frontend coverage collection and valid report generation are required. Coverage percentages are informational; neither workflow enforces an 80% or other percentage threshold. The chosen test boundary is narrower than all repository test assets, so any percentage must be interpreted within that boundary.

The Frontend full image build is a daily required check. The Backend full image is built manually with `--pull --no-cache` for acceptance evidence and records its inputs, resolved base image, and output metadata. Neither workflow pushes an image to a registry or runs Ollama on GitHub runners. Locked application dependencies and recorded model revisions improve repeatability, but mutable base-image tags and external package sources mean bit-for-bit reproducibility is not claimed. Digest pinning is deferred until evidence justifies the maintenance cost.

## CI and real-AI evidence boundary

| GitHub CI proves | Local WSL / Compose with Ollama proves |
| --- | --- |
| Selected deterministic Backend software contracts, API/failure behavior, temporary SQLite, mocked AI dependency boundaries | Native and Compose runtime, local persistence, model loading, real FAISS retrieval and CrossEncoder reranking |
| Frontend state, request, URL and controlled SSE contracts | `qwen3:8b` generation, Ollama/GPU integration, and real RAG behavior |
| Frontend production/image builds and static Compose configuration validity | Service startup/readiness and end-to-end behavior in the user's environment |

Mocked CI contracts are not real-AI end-to-end tests. Browser E2E remains a deferred local asset. Phase D retrieval/reranking evaluation, answer grounding, latency measurement, and observability were intentionally outside Phase C and were implemented later in Phase D.

## Protected `main`

The active `main-pr-quality-gate` ruleset requires a pull request and strict success of exactly `backend-contracts`, `frontend-contracts`, `frontend-image`, and `compose-config`. It requires zero reviewer approvals, blocks force pushes and deletion, and has no routine bypass actor. A validation PR exercised a failing required check followed by green checks and restored merge eligibility. Normal changes to `main` use this protected PR path.

## Evidence and deferred work

The C1 prerequisite fixes established the 41-case Backend marker selection, Frontend `test:ci`, deterministic harness behavior, and a regression test for the former `/api/api` URL defect. C2's daily workflow has successful PR and `main` runs. C3's full Backend image cold build succeeded on the accepted Phase C `main` revision ([run evidence](https://github.com/Henric0612/rag-news-intelligence-platform/actions/runs/34498857441)). C4's rule is active and was exercised by a temporary validation PR. C5 synchronizes the documentation and validates the same four checks through a protected documentation PR. GitHub run history, rather than retained artifacts alone, is the evidence for completed historical builds.

Current deferred items:

- **Pre-existing debt:** Browser E2E readiness; security/performance harness validation; broader configuration and persistence-path issues; full-repository lint/type gates and Frontend chunk optimization.
- **Build improvement:** base-image digest pinning and dependency-update automation, to revisit when their cost and benefit are measured.
- **Later platform work:** cloud deployment, Kubernetes, distributed serving, and production secrets/TLS/migration infrastructure.
