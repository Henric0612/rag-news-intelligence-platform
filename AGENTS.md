# AGENTS.md

## Repository Purpose

`rag-news-intelligence-platform` is a local-first RAG engineering portfolio project.

Its purpose is to demonstrate credible end-to-end AI application engineering across:

- content ingestion and knowledge management;
- embedding, FAISS retrieval, and reranking;
- context construction and local LLM generation;
- Flask API and Vue frontend integration;
- testing and CI;
- containerized reproducibility;
- RAG evaluation;
- latency measurement and runtime observability.

The project is:

> **production-oriented, but not production-ready.**

Do not present or evolve it as a production platform unless a future task explicitly establishes that scope.

---

## Core Engineering Principle

> **Evidence before complexity.**

Before introducing a component, abstraction, dependency, service, or infrastructure layer, confirm that it solves a demonstrated problem or materially improves engineering evidence.

Prefer:

- minimal necessary architecture;
- reproducible behavior;
- explicit trade-offs;
- preservation of working behavior;
- changes with clear engineering or portfolio value.

Do not add technology merely because it is common in production environments or attractive on a résumé.

---

## Established Engineering Baseline

Engineering Phases B, C, and D are complete.

Treat their accepted behavior and evidence as the current project baseline, not as future implementation work.

The established system includes:

- Flask / Gunicorn backend;
- Vue / Vite / Caddy frontend;
- SQLite persistence;
- FAISS retrieval;
- Sentence Transformers embeddings;
- CrossEncoder reranking;
- Ollama-backed local generation with `qwen3:8b`;
- Docker Compose local orchestration;
- GitHub Actions CI;
- versioned RAG evaluation;
- request and stage latency instrumentation;
- process-local RAG runtime metrics.

Authoritative detail lives in:

- `README.md`
- `Backend/README.md`
- `Frontend/README.md`
- `Docs/Phase-C-CI.md`
- `Docs/Phase-D-Evaluation.md`
- `Backend/evaluation/README.md`

Do not duplicate detailed metrics, CI contracts, dependency versions, or reproduction procedures here when an authoritative repository artifact already maintains them.

Phase D measurements are informational engineering evidence.

Do not reinterpret them as:

- production SLOs;
- throughput guarantees;
- regression thresholds;
- production-news quality claims;
- proof that reranking improves aggregate quality.

---

## Development Environment

Primary development is WSL-native.

Expected architecture:

```text
Windows
└── VS Code + Remote-WSL
    └── WSL2 / Ubuntu
        └── repository on the Linux filesystem
```

For ordinary repository development:

- keep the repository on the WSL Linux filesystem rather than `/mnt/c/...`;
- run Git, Python, Node, tests, builds, and development tooling inside WSL;
- use the project-managed Python environment rather than the system Python for backend work;
- use repository-defined frontend tooling rather than Windows-side Node/npm;
- do not route normal development through `wsl.exe`, PowerShell, or Windows development binaries.

Local container execution uses:

> **Docker Desktop + WSL Integration**

Do not install or configure a second Docker Engine daemon inside Ubuntu unless explicitly required by a future task.

Ollama remains a WSL host service and is not a Compose service.

Native WSL development is the preferred edit/debug loop; Compose provides the reproducible container workflow.

Do not redesign the Docker, WSL, GPU, Ollama, or host-networking architecture without explicit scope and supporting evidence.

---

## Agent Workflow

For architecture-heavy, ambiguous, or substantial multi-file work, use:

> **Explore → Plan → Human Review → Implement → Verify → Independent Review**

### Explore

Inspect the real repository before proposing changes.

Use current:

- code;
- configuration;
- tests;
- Git state and history;
- runtime behavior;
- authoritative documentation

as evidence.

Do not rely only on README claims when stronger implementation evidence is available.

### Plan

Plan when meaningful implementation or architectural decisions remain unresolved.

A useful plan defines:

- objective;
- scope;
- constraints;
- affected components;
- important trade-offs;
- validation criteria;
- Definition of Done.

If an approved implementation plan or exact specification already exists, execute it rather than redesigning it.

Reopen an approved decision only when new evidence invalidates an assumption.

Small and obvious changes do not require ceremonial planning.

### Human Review

Preserve a human approval point for consequential architecture, scope, or irreversible decisions.

Do not silently expand an accepted task.

### Implement

Make the smallest coherent change that satisfies the objective.

Preserve unrelated behavior and unrelated working-tree changes.

Do not bundle unrelated refactoring or cleanup into scoped implementation work.

### Verify

Implementation is not complete until relevant behavior has been validated with executable evidence.

### Independent Review

For substantial changes, prefer a fresh-context review of the resulting diff and validation evidence.

Review should look for:

- requirement gaps;
- regressions;
- unsupported claims;
- accidental scope expansion;
- missing validation;
- unnecessary complexity.

If mandatory findings exist, perform bounded repairs and review again.

---

## Change Discipline

Before editing tracked files:

1. inspect the working tree;
2. inspect the relevant implementation path;
3. understand relevant tests and configuration;
4. preserve unrelated changes;
5. identify the smallest valid change.

Do not silently fix:

- pre-existing test failures;
- warnings;
- dependency debt;
- unrelated technical debt;
- unrelated documentation drift

unless they directly block the current task.

Record unrelated findings separately and defer them.

---

## Validation

> **Running is not enough. Validate behavior.**

Use the smallest relevant validation first, then broaden when justified.

Depending on scope, validation may include:

- targeted unit or integration tests;
- backend or frontend contract suites;
- frontend production build;
- Docker image build;
- Compose configuration;
- startup and health/readiness;
- native WSL workflow;
- container workflow;
- persistence behavior;
- dependency failure behavior;
- end-to-end RAG behavior;
- evaluation tooling;
- CI workflow evidence.

Never report a test, build, benchmark, workflow, or runtime check as passing unless it was actually executed or verified from authoritative evidence.

Distinguish clearly between:

- environment failure;
- application failure;
- regression introduced by the current change;
- pre-existing repository issue;
- deferred future improvement.

Do not report one category as another.

---

## Git and Delivery

Inspect `git status` and relevant diffs before repository changes.

Do not:

- commit;
- push;
- create or delete branches;
- rewrite history;
- open or merge pull requests

unless the current task explicitly authorizes the action.

When delivery to `main` is requested, preserve the repository's documented protected-main PR and CI workflow.

Do not bypass established branch or CI governance merely to complete a task faster.

Never commit:

- real secrets;
- credential-bearing `.env` files;
- local databases;
- FAISS runtime indexes;
- uploads;
- model binaries or caches;
- build outputs;
- local evaluation reports;
- machine-specific runtime artifacts.

---

## Destructive and Host-Level Operations

Treat destructive or host-level operations as approval-gated.

Examples include:

- database reset or destructive migration;
- `docker compose down -v`;
- Docker volume deletion;
- destructive filesystem operations;
- history-rewriting Git operations;
- WSL configuration changes;
- Docker daemon changes;
- host package or driver changes;
- Ollama service changes.

Do not modify the host environment merely to work around a repository problem unless explicitly approved.

---

## Security Scope

Security is not a standalone engineering workstream unless explicitly requested.

Avoid obvious anti-patterns such as:

- committed secrets;
- unnecessary privileged containers;
- unnecessary Docker socket mounts;
- unnecessary public host-port exposure.

Prefer straightforward secure defaults when they do not create disproportionate complexity.

Do not expand ordinary work into:

- Kubernetes security;
- supply-chain hardening;
- rootless-container architecture;
- enterprise security infrastructure

without demonstrated need and explicit scope.

---

## RAG and Evaluation Discipline

Do not redesign the RAG pipeline as a side effect of infrastructure, CI, documentation, or operational work.

Changes to:

- ingestion;
- embeddings;
- retrieval;
- reranking;
- context construction;
- generation;
- refusal behavior;
- evaluation methodology

must be explicitly in scope and validated at the appropriate layer.

Preserve the distinction between:

- deterministic software validation;
- synthetic evaluation evidence;
- human-reviewed answer quality;
- local runtime observations;
- production-quality claims.

Do not convert informational evaluation results into quality gates without an explicit engineering decision.

---

## Portfolio and Documentation Discipline

This repository supports a credible engineering career narrative.

Portfolio value must come from demonstrated engineering judgment and evidence, not technology count.

For README, architecture documentation, résumé-oriented material, or engineering claims:

- support claims with repository or runtime evidence;
- describe limitations explicitly;
- distinguish measured results from aspirations;
- do not exaggerate scalability, reliability, security, AI quality, or production readiness;
- preserve the project's AI-assisted-development disclosure.

The preferred engineering story is:

> increasingly reproducible, testable, evaluated, and observable engineering built from demonstrated needs.

Not:

> accumulation of production technologies for their own sake.

Documentation should describe the system that actually exists.

If code and documentation disagree, investigate and determine the current intended behavior before changing either.

---

## Scope Discipline

If useful work is discovered outside the current task:

> **record it, classify it, and defer it.**

Do not automatically turn a focused task into a new engineering phase.

Future evolution may include cloud deployment, Kubernetes, distributed serving, deeper model-serving infrastructure, or broader observability, but only when a future objective establishes the need.

---

## Repository Identity

Canonical project name:

```text
rag-news-intelligence-platform
```

Canonical GitHub repository:

```text
Henric0612/rag-news-intelligence-platform
```

Do not introduce legacy project names into new implementation or documentation unless the historical reference is intentional.