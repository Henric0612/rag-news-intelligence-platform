# Phase D — Evaluation and observability

This local-first engineering baseline is **production-oriented, but not
production-ready**. Phase D measures the existing RAG pipeline and exposes its
runtime behavior. It does not optimize models, prompts, chunking or deployment.
Real AI results are informational and manually accepted; they are not quality
targets, regression thresholds, SLOs or required CI gates.

## Evidence and provenance

D1–D4 were accepted before D5. Their independent commits are:

| Stage | Accepted implementation commit |
| --- | --- |
| D1, evaluation foundation | `25754cbb0e4c9a2bfaae066d1049559333278dc5` |
| D2, retrieval and reranking | `0c6826fcae2f83902dd16665e5df8936c7f0f4b1` |
| D3, answer and grounding | `94ff9b66402125a5994ea71b1b19fa6d33451874` |
| D4, latency and observability | `c03720683adb619f40781945a28300bcdcd8a5c4` |

The versioned [golden dataset](../Backend/evaluation/golden_v1.json) and
[evaluation code and rubric](../Backend/evaluation/README.md) are the public
reproduction inputs. Dataset SHA-256:
`29484f908f1846901b3ee0ff623996879e131d88f52f57c415473631223fbea2`.
Local raw reports, model caches, credentials and user databases are not
repository artifacts or public reproduction prerequisites.

D5 verified the accepted D3 raw report against its committed provenance. D2's
original temporary report was unavailable; the unchanged runner was rerun on
2026-10-01 at `14:57:50.823826 UTC`. Its full-precision aggregate values below
match the accepted D2 report's published precision. This corroboration does
not replace D2's accepted run or introduce a new quality gate.

D4's retained review report, dated `2026-10-01T07:20:48.629860+00:00`, preserves
its accepted measurements and runtime findings. Its temporary raw JSON and
logs are no longer available after the WSL restart. The latency table preserves
the review report's two-decimal precision; no additional raw precision is
claimed. Fresh D5 runtime smoke is separate from that accepted benchmark.
There are no links here to temporary runtime files or personal directories.

## D1 — Fixed evaluation foundation

The original, fictional Chinese news-style corpus has **24 KnowledgeItems and
30 questions: 28 answerable and 2 unanswerable**. Ordinary single-record and
multi-record questions form the main set; boundary cases include confusing
entities, long records, evidence beyond the first visible fragment, and facts
beyond the current first-500-character search truncation.

Each question has a stable ID, scenario tags, relevance grades, expected
facts, evidence record IDs and quoted spans, answerability, and a refusal basis.
Grade 0 is irrelevant to the exact question, grade 1 supplies partial/contextual
support, and grade 2 directly supports an expected fact. Evidence spans use
Python Unicode character indexes with an exclusive end; the schema checks
that `content[start:end]` equals the quote. No-answer cases have no expected
facts/evidence spans; contextual grade-1 records may still exist.

The isolated loader creates private temporary SQLite and a 384-dimensional
FAISS IndexFlatIP with an empty ID mapping. It loads only fixed records and
never opens the configured development database or a Compose volume. Real
runners populate vectors through the production embedding path. The context
manager disposes the database engine and deletes its temporary directory.

Deterministic math rejects duplicate candidate IDs and nonpositive K. Recall
counts grades 1 and 2, returns null for unanswerable/zero-relevant cases, and
excludes nulls from its aggregate. nDCG uses gains 0/1/3 with log2 discount;
zero ideal gain yields 0. MRR uses the first grade 1 or 2. Short result lists
are allowed. These contracts test evaluator correctness independently of AI.

**A fixed synthetic dataset provides reproducible engineering evaluation. It
does not represent real news distributions or establish overall production
quality.** Labels and questions were not edited to improve scores.

## D2 — Retrieval and reranking baseline

Manual records are embedded using their content, matching ingestion. The
production search retrieves up to 20 candidates and scores that same candidate
set with the existing CrossEncoder. Top-5 comparisons therefore isolate
ranking changes rather than changing the candidate pool.

| Aggregate | Value |
| --- | ---: |
| Recall@20, 28 answerable questions | 0.9464285714285714 |
| nDCG@5 before reranking, all 30 questions | 0.7845272011537335 |
| nDCG@5 after reranking, all 30 questions | 0.7683627411698059 |
| MRR@5 before reranking, all 30 questions | 0.7833333333333333 |
| MRR@5 after reranking, all 30 questions | 0.7777777777777778 |
| nDCG improved / regressed / unchanged | 5 / 7 / 18 |
| Reranking skipped / keyword fallback | 0 / 0 |

Q028/Q029 are excluded from Recall; their contextual labels still participate
in nDCG/MRR. **Reranking did not improve aggregate quality in this baseline.**
FAISS inner-product similarity and raw CrossEncoder scores have different
scales and cannot be directly compared.

Per-question reports bind candidate ID, relevance grade, retrieval score/rank
and actual reranking score/rank. Missing relevant IDs and missing direct
evidence IDs are separate fields. Q015's evidence record 1015 missed the
top-20 candidate set; this is a retrieval miss, not a reranker failure. Q016
missed a partially relevant record while retaining direct evidence. Q027's
relevant record 1017 moved from candidate rank 2 to reranked rank 19: evidence
was retrieved but ranking worsened. Q006 improved from rank 2 to rank 1.

Accepted correctness repairs preserve candidate identities when a database
record/mapping is missing, retain original FAISS ranks instead of pairing a
compressed record list with unrelated scores, search against actual index
size, and replace placeholder reranking scores with real CrossEncoder scores.
No retrieval architecture, dataset or model tuning was introduced.

## D3 — Answer, grounding and refusal

The authoritative protocol calls the production answer path once for each of
30 questions. The first answers and retrieval traces are checkpointed without
replacement. Six preselected cases receive two additional calls each:
Q001 (ordinary), Q002 (ambiguity), Q007 (truncation), Q025 (multi-document),
Q028 (refusal), Q030 (truncation/zero-valued fact). These 12 additional answers
are repeatability observations, not a second authoritative baseline or a
statistically significant sample.

Human Review scores **factual correctness, completeness, grounding and refusal
correctness independently**, using 0/1/2 rubric grades and quoted corpus spans.
Literal fact matches, number/date anchors, visible evidence and refusal phrase
checks are deterministic diagnostic cues. They cannot judge valid paraphrases,
all unsupported additional claims or semantic correctness; the generated review
queue leaves all four rubric axes pending until human review. The historical
`quality_score` heuristic is not AI quality ground truth.

The original **2026-09-28 authoritative baseline artifacts were lost**. A full
replacement run was performed and formally accepted by Human Review; it was
not recovery of the original baseline. Accepted replacement:

- Run ID: `d3-22a9fa43-08d1-48eb-b07e-5ab8fef974c5`.
- Raw SHA-256: `917365cddfa783b02e31a8c369f3c06b5eb80c62a1d1e3b4d7516dc6d06d2eb0`.
- Raw metadata: `2026-09-28T23:46:26.608052+00:00` through
  `2026-09-28T23:52:32.681456+00:00` (UTC; the local review package is dated
  2026-09-29).
- Accepted verdicts: `D3_HUMAN_REVIEW = PASS`, `D3_STATUS = PASS`.

Accepted findings cover 30 questions (28 answerable, 2 unanswerable), including
**five retrieval/context/truncation-limited cases: Q007, Q015, Q023, Q027
and Q030**. Q015 is a top-20 retrieval
miss. Q023 exposes the first-500-character truncation boundary. Q027 gives a
partial answer because required evidence is limited in the actual context.
Q028/Q029 correctly refuse the missing requested information. Representative
repeatability cases retain their core factual/refusal outcomes; wording and
generation may vary. No aggregate human accuracy percentage is inferred from
rule classifications.

A grounding limitation remains: some answers turn “no evidence in the current
context” into the broader claim “this information is absent from the knowledge
base.” D5 records this finding and does not change the prompt. **Source lists
and retrieved documents do not establish sentence-level citation attribution;
sentence-level citation correctness has not been validated.**

## D4 — Latency and observability

Accepted native runtime: WSL2 / Ubuntu, Linux
`6.6.114.1-microsoft-standard-WSL2`, CPU embedding/reranking, host Ollama with
GPU inference on **NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB**. Earlier
RTX 3060 Ti documentation was an expectation, not the measured hardware.
Embedding is `sentence-transformers/all-MiniLM-L6-v2`; reranker is
`cross-encoder/ms-marco-MiniLM-L-6-v2`. The container pins their revisions in
[Backend/Dockerfile](../Backend/Dockerfile).

D3 and D4 used exact tag `qwen3:8b`, digest
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
Explicit generation parameters: `temperature=0.7`, `num_predict=2048`,
`top_p=0.9`, `top_k=40`; remaining Ollama/LangChain parameters retain defaults.
RAG settings: candidate K=20, rerank K=5, context limit=4000 characters,
reranking enabled, web fallback disabled.

### Accepted latency observations

Production Flask RAG routes used isolated D1 SQLite/FAISS. Q001/Q025 each had
two warm observations per mode: **normal n=4 and streaming n=4**. Cold and
streaming warmup observations, diagnostic probes and D2/D3 calls are excluded.
Metadata timestamp: `2026-10-01T07:12:48.199179+00:00`; finish:
`2026-10-01T07:14:52.320444+00:00`.

| Stage (ms, accepted report precision) | Normal p50 | Normal p95 | Streaming p50 | Streaming p95 |
| --- | ---: | ---: | ---: | ---: |
| Query embedding | 7.89 | 10.38 | 7.79 | 10.31 |
| Candidate retrieval | 0.16 | 0.16 | 0.18 | 0.22 |
| Record loading | 1.32 | 1.92 | 1.30 | 1.48 |
| Reranking | 114.37 | 849.20 | 103.11 | 856.43 |
| Context construction | 0.07 | 0.09 | 0.08 | 0.10 |
| Generation | 5935.31 | 9646.39 | 9142.87 | 11276.72 |
| Total | 6136.77 | 10487.93 | 9280.68 | 12162.51 |
| Application streaming TTFT | null | null | 5838.51 | 9529.38 |
| Streaming completion | null | null | 9280.51 | 12162.33 |

App/service cold request: total 9034.79 ms, initialization 138.40 ms. Corpus
embedding/index setup was already complete (separately 602.46 ms) and Ollama
already had `qwen3:8b` resident. It is not a wholly cold model/GPU run.
Streaming warmup total was 5943.64 ms. An earlier empty-residency observation
of 17619.28 ms overlapped Docker build CPU contention and was not used for
final warm statistics.

Generation is the dominant slow stage. Percentiles use nearest rank; with
n=4, p95 is the maximum. These local small samples are **not SLO/SLA,
throughput, capacity, concurrency or load benchmarks**. Streaming TTFT is
request start to the first **non-empty application content event**, not model
internal first token or browser first byte. Streaming timing includes consumer
iteration waits. Stage sums need not equal total, which also includes route
wrapping, history writes and instrumentation; unexecuted stages are null.

### Operational contracts

Normal and streaming requests use UUID correlation through `X-Request-ID` and
structured events. Valid external UUIDs are normalized; invalid IDs generate a
new UUID. Events cover start/end, stages, candidate count, reranking state,
fallback/error categories, first content and stream completion. SSE interruption
closes upstream iterators, ends one correlated request as interrupted, and
leaves completion timing null instead of counting success.

Reranking states: not reached, executed, disabled, unavailable, empty or failed.
Fallbacks distinguish no vectors, no semantic results, retrieval error, web
search and legacy generation; errors distinguish retrieval, reranking,
generation, context, application, interruption and no-results conditions.
A recovered request can succeed while retaining its classified stage error.

`GET /api/rag/metrics` reuses `User.role` and `admin_required()`: unauthenticated
**401**, ordinary user **403**, administrator **200**. The response includes
process/instance identity, startup/reset time, requests, reranking, fallbacks,
errors and stage latency summaries. Counters cover the instance lifetime;
each stage retains its latest 2048 non-null samples, with retained `count` and
lifetime `observed_count`. Metrics are thread-safe and **process-local**, single
worker, nonpersistent; a process/app-instance restart clears them and changes
the instance identity. SQLite/FAISS persistence is independent of that reset.
There is no exporter, collector, dashboard or distributed trace infrastructure.

Privacy is metadata-only: no full query, context, prompt, answer, authentication
value, user identity or raw exception message in structured events/metrics.
Accepted native and isolated Compose checks found no full-text RAG payload
leakage. Business API responses still carry answers and sources; operational
metadata does not establish a broader privacy claim for every application path.

## Reproduction

Run commands from the repository root. Use the existing
[Backend setup](../Backend/README.md), declared dependencies and native model
caches. Ollama must serve `qwen3:8b` on the host with GPU available. Do not run
`init_db.py`, reset a development database, or mount real data for evaluation.

### Deterministic / CI-compatible

The existing backend CI selector includes D1 schema/math/isolation, D2 identity
and ranking evaluation, D3 rule/report/protocol validation and D4 observability
contracts. Reports can be generated in a chosen external output directory:

```bash
D5_OUTPUT=$(mktemp -d)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES='' \
COVERAGE_FILE="$D5_OUTPUT/coverage" .venv/bin/python -m pytest \
  -c Backend/pytest.ini Backend/tests -m ci --cov=Backend \
  --cov-config=Backend/tests/.coveragerc --cov-report=term \
  --cov-report="xml:$D5_OUTPUT/coverage.xml" \
  --junitxml="$D5_OUTPUT/junit.xml"
git diff --check
```

For a focused deterministic run:

```bash
.venv/bin/python -m pytest -c Backend/pytest.ini \
  Backend/tests/unit/test_evaluation_foundation.py \
  Backend/tests/unit/test_retrieval_evaluation.py \
  Backend/tests/unit/test_answer_evaluation.py \
  Backend/tests/unit/test_rag_observability.py
```

GitHub CI verifies **deterministic software contracts**. It does not supply
real embedding/CrossEncoder/Ollama/GPU quality or latency evidence. Existing
Daily CI checks remain `backend-contracts`, `frontend-contracts`,
`frontend-image`, `compose-config`; the separate existing Backend Image
Validation builds the full backend image. See [Phase C](Phase-C-CI.md).

### WSL native, real AI

Choose a new external directory and filenames; retain raw reports for review.
A newly generated D3 run has a new ID and does not become the accepted
replacement baseline without Human Review.

```bash
D5_OUTPUT=$(mktemp -d)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python \
  -m Backend.evaluation.retrieval --output "$D5_OUTPUT/retrieval.json"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python \
  -m Backend.evaluation.answer_run --output "$D5_OUTPUT/answers.json"
.venv/bin/python -m Backend.evaluation.answer_report "$D5_OUTPUT/answers.json"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python \
  -m Backend.evaluation.latency --output "$D5_OUTPUT/latency.json" --repetitions 2
```

The D3 command is for intentional full protocol reproduction, **not needed for
D5 final smoke**. Latency uses real routes, normal/SSE observations, auth,
privacy, interrupted stream and fallback probes on isolated storage. It is a
finite observation runner, not a load tool. Deterministic tests and real AI
runs should be sequential to avoid shared test-path/CPU contention.

### Isolated Compose, real HTTP

Use Docker Desktop + WSL Integration and the existing topology. A distinct
project creates its own volume; abort if that project volume already exists.
Select unused loopback ports. Generate temporary validation-only secrets in
shell memory and do not write them into versioned files:

```bash
D5_PROJECT=rag-phase-d-check
if docker volume inspect "${D5_PROJECT}_rag_data" >/dev/null 2>&1; then
  echo 'Choose a new isolated project name'; exit 1
fi
export SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
export BACKEND_PORT=15005 FRONTEND_PORT=13005
export OLLAMA_HOST=http://host.docker.internal:11434
docker compose --env-file /dev/null -p "$D5_PROJECT" -f compose.yaml config --quiet
docker compose --env-file /dev/null -p "$D5_PROJECT" -f compose.yaml up -d --build --wait
```

Inspect the backend mount before seeding; it must name the isolated project's
`rag_data` volume. Seed only this new database with the versioned synthetic
corpus and disposable roles, without reset/drop:

```bash
docker inspect "$(docker compose -p "$D5_PROJECT" ps -q backend)" \
  --format '{{json .Mounts}}'
docker compose -p "$D5_PROJECT" exec -T backend python - <<'PY'
from Backend.app import create_app
from Backend.models import db, KnowledgeItem, User
from Backend.evaluation.dataset import load_dataset
from Backend.services.vector_service import get_vector_service
app = create_app()
with app.app_context():
    assert KnowledgeItem.query.count() == 0 and User.query.count() == 0
    dataset = load_dataset()
    for item in dataset['records']:
        db.session.add(KnowledgeItem(id=item['id'], title=item['title'],
            content=item['content'], category=item['category'],
            source_type='manual', status='published', language='zh'))
    for role in ('admin', 'user'):
        user = User(username='evaluation-'+role, email=role+'@evaluation.invalid',
                    role=role, is_email_verified=True)
        user.set_password('evaluation-only-disposable'); db.session.add(user)
    db.session.commit()
    vector = get_vector_service()
    assert vector.build_faiss_index(vector.batch_vectorize(
        [r['content'] for r in dataset['records']]),
        [r['id'] for r in dataset['records']])
PY
```

Login through `/api/auth/login` with those disposable users and use the returned
access tokens in memory. Verify normal `/api/rag/ask` and `stream:true` SSE,
correlation IDs, 401/403/admin 200 metrics, `/api/health`, quick/full
`/api/ready`, frontend and its API proxy, and host Ollama connectivity from the
backend. Inspect actual logs/metrics against the synthetic queries, contents,
answers and tokens for full-text leakage. After `docker compose -p
"$D5_PROJECT" restart backend`, SQLite records, users and FAISS vectors must
persist while metrics counters reset and process-instance identity changes.
Stop only the isolated project using `docker compose -p "$D5_PROJECT" down`.
Never run `down -v` on the real project or remove its volume. A synthetic volume
can be removed separately only after confirming its identity and stopping its
containers; saved runtime reports stay outside Git.

## D5 local acceptance — 2026-10-01

| Check | Observed result |
| --- | --- |
| Existing backend CI selector, including D1–D4 | 111 passed, 122 deselected; valid Coverage/JUnit XML; one existing jieba/pkg_resources warning |
| WSL native real-AI smoke | Q001 completed with 20 candidates, 5 reranked sources, actual context/generation stages and host Ollama GPU residency |
| Unchanged D2 real evaluator | All 30 questions completed; aggregate and representative failure/ranking evidence corroborated |
| Accepted D3 provenance | Replacement raw run ID and SHA-256 verified; full D3 generation was not repeated |
| Isolated Compose build/startup | Existing Backend/Frontend Dockerfiles built successfully; both services healthy |
| Real HTTP normal and streaming RAG | Two successful correlated requests; 20 candidates and executed reranking; SSE timing ordered |
| Health/readiness and frontend proxy | Liveness, quick/full readiness, frontend and proxied API health all HTTP 200 |
| Metrics authorization | Unauthenticated 401, ordinary user 403, administrator 200 |
| Persistence and metrics reset | After backend restart: 24 synthetic records, 2 roles, 24 vectors/mapping entries retained; all request/latency sample counts zero; new metrics instance ID |
| Source and privacy | All versioned Backend runtime Python source hashes match the built image; actual logs/metrics contain no full synthetic query/content/answer, auth token or validation secret |
| AI wiring | Container reaches host Ollama with qwen3:8b; host GPU residency verified |

Only a new isolated project/volume was seeded. The original user-data volume
was never mounted. Runtime reports, scripts and test outputs were kept outside
the repository. The fresh smoke results confirm behavior and do not replace
accepted D3/D4 quality or latency baselines. Remote final-SHA acceptance is a
separate mandatory gate below; local PASS alone is not Phase D completion.

## D5 acceptance checklist and final SHA invariant

The documentation commit is accepted only when **all** items hold:

- D1–D4 accepted; D4 independently committed; no outstanding implementation diff.
- This guide, root README and relevant Backend documentation agree with code,
  accepted evidence and current commands; no temporary/personal artifact links.
- Existing backend CI contract including D1–D4 passes; coverage/JUnit valid;
  `git diff --check` passes.
- Fresh WSL real-AI retrieval/reranking/context/generation smoke passes.
- Fresh isolated Compose build/startup, health/readiness, normal/SSE RAG,
  host Ollama, metrics access, privacy and restart/persistence checks pass.
- Exact diff/staged files contain documentation only (minimal ignore rules only
  if necessary); no production/Frontend/Compose/workflow/dependency changes,
  secrets, user data, SQLite, FAISS, models, coverage or runtime reports.
- The temporary untracked implementation plan is deleted after its relevant
  requirements have been absorbed here; it is never committed.
- `main` is protected: final documentation changes are committed on a
  temporary closeout branch, which is pushed and merged through a PR targeting
  `main`. Never push directly to `main`, force push, or change protection.
- The PR merges only after the four required checks `backend-contracts`,
  `frontend-contracts`, `frontend-image` and `compose-config` succeed, using a
  normal merge mechanism allowed by the repository rules.
- After the merge, fetch origin and read the actual `origin/main` SHA; only this
  post-merge SHA is the candidate final SHA.
- On that exact final main SHA, all four existing Daily CI checks are
  successful and **Backend Image Validation is SUCCESS on that same SHA**.
- Local main is safely synchronized to the accepted origin/main, the temporary
  closeout branch is cleaned up, staged/tracked/untracked state is clean, and
  no validation branch or runtime artifact entered the repository.

After the PR merges, identify the final SHA, then invoke and inspect the
existing workflows on it:

```bash
git fetch origin
FINAL_SHA=$(git rev-parse origin/main)
gh workflow run backend-image.yml --ref main
gh run list --commit "$FINAL_SHA"
git rev-parse HEAD origin/main
git status --short
```

GitHub PR history and Actions runs are the evidence source for the exact final
SHA; this guide does not record it, because any documentation change produces
a new one.

Confirm workflow identity, run identity, head SHA, completed status and success
conclusion, including the four jobs inside Daily CI. An old D1–D4 success
cannot substitute for final-SHA acceptance. **Any subsequent commit invalidates
both final CI/image evidence and requires validation on the new final SHA.**
The final verdict is COMPLETE only with the entire checklist satisfied;
otherwise report INCOMPLETE and the exact blockers. Once satisfied, stop.

## Deferred findings

Record these boundaries without fixing them in D5: synthetic-corpus bias;
independent real-news validation set; Q015 retrieval miss; aggregate reranking
regression; first-500-character truncation and future chunking/retrieval work;
context-absence wording; generation variability; local small-sample latency
and generation cost; application streaming timing semantics; process-local
metrics and restart clearing; coarse admin role; future exporter/collector/
dashboard; existing browser E2E and old performance/security test debt.
Kubernetes, cloud deployment and distributed serving remain later work.
