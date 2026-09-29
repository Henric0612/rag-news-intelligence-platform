# Phase D / D1 evaluation foundation

`golden_v1.json` is a fixed, original, fictional Chinese news corpus. IDs are
stable `KnowledgeItem.id` integers. Content and questions were written for this
project; they do not describe real events or personal data. The JSON is the
reviewable source of truth. Do not change labels or evidence to improve a model
score; version a revised corpus instead.

Each question has scenario tags, a query, relevance grades keyed by record ID,
`relevant_ids` (all grades 1 or 2), expected facts, evidence IDs, answerability,
and a refusal reason for no-answer cases. Character offsets are Python Unicode
string indexes: `content[start:end] == quote`, with `end` exclusive. A fact may
have several evidence spans. `evidence_ids` is the sorted union of their record
IDs. For no-answer questions, expected facts and evidence IDs are empty; the
refusal reason states the missing information. Grade-1 records can be related
to a no-answer question without containing the requested answer.

Relevance grades:

- **0**: does not help answer this exact query, even if names or topics overlap.
- **1**: partially or contextually relevant, but does not directly establish the
  requested answer by itself.
- **2**: directly supports at least one requested fact. Every cited evidence
  span must belong to a grade-2 record.

`recall_at_k` requires the question's explicit `answerable` flag, counts grades
1 and 2 as relevant, and returns `None` for zero relevant records or
`answerable=False`; exclude `None` from aggregate recall.
`ndcg_at_k` uses gains 0/1/3 and log2 rank discount; ideal DCG 0 yields 0.
`mrr_at_k` uses the first grade 1 or 2. All metric functions reject duplicate
retrieved IDs and nonpositive K; fewer than K results are accepted. The caller
passes integer record IDs, so convert JSON relevance keys with `int(key)`.
Primary future cutoffs are Recall@20 and nDCG@5, with MRR@5 for reranking.
These D1 functions do not run retrieval or report model quality.

## D2 retrieval and reranking baseline

From the repository root in the WSL native environment, with the existing
local embedding and CrossEncoder model caches available, run:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m Backend.evaluation.retrieval --output /tmp/rag-d2-retrieval-baseline.json
```

The runner loads the fixed D1 records into temporary SQLite and FAISS storage,
indexes each manual record's `content` through the production embedding path, and calls
the production semantic search and reranking methods for every question. The
report has aggregate means plus one row per question with every candidate's
ID, label, retrieval rank/score, and reranked rank/actual CrossEncoder score.
It compares top-5 metrics on the same top-20 candidate set. No-answer questions
are excluded only from Recall@20; their nDCG@5 and MRR@5 still describe the
grade-1 contextual labels. `missing_relevant_ids` and `missing_evidence_ids`
separate partial relevant-item recall from failure to retrieve direct evidence.
The JSON file is a local run artifact; do not add it to Git or use its AI scores
as a CI quality gate. Run `pytest -c Backend/pytest.ini Backend/tests -m ci` for
the deterministic contract tests.

`isolated_evaluation()` creates a private temporary SQLite database and an
empty 384-dimensional FAISS IndexFlatIP plus `{}` ID mapping. It loads all
fixed records into the `KnowledgeItem` table, yields an app context and paths,
then disposes the engine and removes the temporary directory. It never calls
the production app factory or reads configured development/Compose paths. The
empty index is storage preparation; D2 must populate real vectors before any
retrieval measurement.

## Human answer review rubric (for D3)

Score each axis independently as **2** (fully meets), **1** (partly meets), or
**0** (fails). Record the question ID, answer text, reviewer, and short rationale.
Use expected facts and quoted spans to decide, not `quality_score`.

| Axis | 2 | 1 | 0 |
| --- | --- | --- | --- |
| Factual correctness | All asserted facts agree with corpus evidence, including valid paraphrases | Correct core fact with a minor imprecision | Wrong entity, number, date, or material claim |
| Completeness | Covers every expected fact, including synthesis across records | Covers some expected facts | Misses all expected facts |
| Grounding | Every material claim is supported by identifiable spans | Main claim supported but another claim only partly supported | Material unsupported claim or contradiction |
| Refusal correctness | Refuses a no-answer question with an accurate reason, or answers an answerable one | Qualified or unclear response without fabricated facts | Incorrect refusal on an answerable question or invented answer to a no-answer one |

For no-answer questions, completeness is 2 when the response explains that the
requested fact is absent and avoids inventing it; factual correctness and
grounding still assess any additional claims. A paraphrase can earn 2 without
copying wording. A multi-document answer earns completeness 2 only when all
required facts are present. A partially supported answer cannot earn grounding
2. An unsupported claim earns grounding 0 if material, even when the expected
fact is also present. Record disagreements for later adjudication.

**A source list is not sentence-level citation correctness.** This rubric
reviews support using spans; D1 does not claim citation correctness validation.

## D3 answer and grounding baseline

Run on the WSL host with Ollama `qwen3:8b`, the existing model caches, and GPU
available. The output path must be outside the repository and must not exist.
For a reviewable authoritative run, choose a persistent external directory
accessible to the reviewer; `/tmp` may be cleared between Codex sessions.
Example for an initial local run:

```bash
mkdir -p "$HOME/rag-evaluation-output"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m Backend.evaluation.answer_run --output "$HOME/rag-evaluation-output/rag-d3-answer-baseline.json"
.venv/bin/python -m Backend.evaluation.answer_report "$HOME/rag-evaluation-output/rag-d3-answer-baseline.json"
```

The runner writes the fixed repeatability selection before generating answers,
then checkpoints each first answer. It calls the production `RAGService.answer_question`
with real isolated D1 records, embeddings, FAISS, CrossEncoder and Ollama. It
does not change the production prompt, context, model or generation parameters.
If interrupted, retain the partial JSON as evidence; start a new run under a
new filename rather than replacing any first answer. The six selected questions
each receive two additional calls after all 30 first calls. The report tool
validates completeness and writes a scored derivative, a JSON review queue,
a three-answer comparison, and a readable human-review Markdown file. It never
rewrites the original first-run answers or retrieval traces.

Rule output records literal fact, number/date anchor, evidence visibility and
refusal phrase cues. These are diagnostic cues, not factual correctness or
grounding grades. Every D1 rubric axis remains pending until a human reviews
the answer against quoted evidence spans, including any unsupported additional
claim. `retrieval_limited` means a required span was not visible in the actual
context; `generation_limited_candidate` and `correct_refusal_candidate` need
human confirmation. All other semantic cases are marked ambiguous. The source
list is not sentence-level citation mapping. Repeated answers describe variation
only and are not a new baseline or statistically significant sample.

### Accepted D3 baseline provenance

The accepted authoritative rerun is `d3-22a9fa43-08d1-48eb-b07e-5ab8fef974c5`;
its raw JSON SHA-256 is
`917365cddfa783b02e31a8c369f3c06b5eb80c62a1d1e3b4d7516dc6d06d2eb0`.
The original 2026-09-28 baseline artifacts were lost from `/tmp`. The full D3
protocol was rerun, and Human Review accepted this new run as the replacement
authoritative baseline, not as a recovery of the original. The recorded verdicts
are `D3_HUMAN_REVIEW = PASS` and `D3_STATUS = PASS`.

Accepted findings: 30 questions (28 answerable, 2 unanswerable); five cases
limited by retrieval, context, or truncation. Q015 missed the top-20 candidate
set; Q023 hit the first-500-character truncation boundary; Q027 gave a partial
answer because of evidence/context limits. Q028 and Q029 correctly refused to
answer. The six preselected repeatability cases kept their core factual or
refusal outcomes. A deferred grounding limitation remains: when evidence is
absent from the current context, some answers overstate that absence as missing
from the entire knowledge base.

Raw and generated runtime artifacts are intentionally not versioned. The fixed
D1 dataset and this repository's D3 runner permit a fresh execution of the
same protocol; a fresh run receives a new ID and is not the accepted raw run.
Full evaluation documentation is deferred to D5.
