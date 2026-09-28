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
