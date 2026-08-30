# AGENTS.md

## Repository Purpose

`rag-news-intelligence-platform` is a local-first RAG engineering portfolio project.

Its purpose is to demonstrate credible end-to-end AI application engineering, including:

- content ingestion and knowledge management;
- embedding, FAISS retrieval, and reranking;
- context construction and local LLM generation;
- Flask API and Vue frontend integration;
- testing, reproducibility, containerization, evaluation, and operational evolution.

The project is:

> **production-oriented, but not production-ready.**

Do not turn it into a production platform unless the current phase explicitly requires that work.

---

## Core Engineering Principle

> **Evidence before complexity.**

Before introducing a new component, abstraction, service, dependency, or infrastructure layer, confirm that it solves a demonstrated problem in the current project.

Prefer:

- minimal necessary architecture;
- reproducible behavior;
- explicit trade-offs;
- preservation of existing working behavior;
- changes that provide clear engineering or portfolio value.

Do not add technology only because it is common in production systems.

---

## Primary Development Environment

Primary local development environment:

```text
Windows 11
└── WSL2 / Ubuntu-24.04
    └── /home/henric/projects/rag-news-intelligence-platform
```

Use the Linux filesystem for repository development.

Do not move the primary repository into `/mnt/c/...`.

Current native development path should remain usable unless a task explicitly changes that requirement.

---

## Current Runtime Direction

The current application architecture is based on:

- Python / Flask backend;
- Vue frontend;
- SQLite;
- FAISS;
- Sentence Transformers embedding;
- CrossEncoder reranking;
- Ollama with `qwen3:8b`.

Ollama currently runs as a WSL host service and uses the local NVIDIA GPU.

Do not change the Ollama, GPU, WSL, or host-networking architecture without evidence and explicit task scope.

---

## Container Runtime

For local containerization, use:

> **Docker Desktop + WSL Integration**

Do not install a second Docker Engine daemon inside Ubuntu unless explicitly required by a future task.

Avoid creating competing Docker runtime states.

Docker Compose is intended for reproducible local container execution and validation.

Native WSL development remains the preferred fast development/debug loop unless explicitly changed.

---

## Working Rules

### Audit Before Change

Inspect the real repository, dependencies, configuration, tests, and runtime behavior before modifying them.

Do not rely only on README claims when code evidence is available.

### Preserve Existing Behavior

Containerization, CI, evaluation, and operational improvements should preserve existing application behavior unless a change is explicitly required.

Do not redesign the RAG pipeline as a side effect of infrastructure work.

### Minimal Change

Prefer the smallest change that satisfies the current objective and validation criteria.

Do not perform unrelated cleanup while implementing a scoped task.

### Existing Issues

Do not silently fix pre-existing test failures, dependency debt, frontend warnings, or unrelated technical debt unless they directly block the current task.

Record unrelated issues separately.

### Destructive Operations

Do not execute destructive database initialization, reset, deletion, migration, or volume removal without first determining the impact.

Treat commands equivalent to `docker compose down -v`, database `drop_all`, or destructive migrations with special care.

---

## Repository Changes

Before editing tracked files:

1. inspect the current working tree;
2. understand the relevant code path;
3. preserve unrelated changes;
4. validate the intended behavior after modification.

Do not commit, push, create branches, or open pull requests unless the task explicitly requests it.

Never commit:

- real secrets;
- `.env` files containing credentials;
- local databases;
- FAISS runtime indexes;
- uploads;
- model binaries;
- build outputs;
- machine-specific runtime artifacts.

---

## Security Scope

Security is not a standalone engineering workstream unless explicitly requested.

Avoid obvious container anti-patterns, including:

- committed secrets;
- unnecessary `privileged` containers;
- unnecessary Docker socket mounts;
- unnecessary public host-port exposure.

Prefer a non-root container user when straightforward, but do not create significant permission or UID/GID complexity solely to satisfy that preference.

Do not expand ordinary Phase B work into rootless Docker, Podman, capability hardening, Kubernetes security, or supply-chain security without demonstrated need.

---

## Phase Boundaries

### Phase B — Containerized RAG Stack

Focus:

- backend and frontend containerization;
- Docker Compose orchestration;
- configuration;
- persistence;
- health/readiness;
- local AI runtime integration;
- reproducible startup and validation.

Do not pull Phase C or D work into Phase B.

### Phase C — CI-Tested AI Application

Focus:

- GitHub Actions;
- automated backend/frontend tests;
- repeatable builds;
- coverage and quality gates.

### Phase D — Evaluated and Observable RAG System

Focus:

- retrieval/reranking evaluation;
- answer grounding;
- latency measurement;
- metrics, tracing, and observability.

### Later

Kubernetes, distributed serving, cloud deployment, and deeper AI platform engineering should only be introduced after earlier foundations justify them.

---

## Naming

Canonical repository identity:

```text
rag-news-intelligence-platform
```

Canonical GitHub repository:

```text
Henric0612/rag-news-intelligence-platform
```

Legacy names such as `XU-AI-RAG` should not be introduced into new implementation or documentation.

Historical references may remain only when their historical meaning is intentional.

---

## Codex Workflow

For architecture-heavy or ambiguous work:

> **Plan → Human Review → Goal**

Use Plan Mode to investigate and design when important engineering decisions remain unresolved.

Use Goal Mode after:

- objective;
- scope;
- constraints;
- approval gates;
- validation criteria;
- Definition of Done

are sufficiently clear.

Do not repeatedly redesign an approved plan during implementation unless new evidence invalidates it.

---

## Validation Principle

> **Running is not enough. Validate behavior.**

Where applicable, verify:

- build;
- startup;
- health/readiness;
- native workflow regression;
- container workflow;
- persistence;
- failure behavior;
- end-to-end RAG behavior.

Distinguish:

> environment failure
> application failure
> pre-existing repository issue
> future-phase improvement

Do not report one category as another.

---

## Scope Discipline

If useful work is discovered outside the current task:

> record it, classify it, and defer it.

Do not automatically expand the current implementation.

The project should become more credible through evidence and validation, not through accumulating infrastructure.
