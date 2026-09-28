"""D2 retrieval and reranking baseline against the fixed D1 corpus."""

import argparse
from datetime import datetime, timezone
import hashlib
import json

from .dataset import DATASET_PATH, load_dataset
from .loader import isolated_evaluation
from .metrics import mrr_at_k, ndcg_at_k, recall_at_k


def evaluate_questions(dataset, search_service):
    """Evaluate the real search interface; accept a fake service for CI contracts."""
    record_ids = {record["id"] for record in dataset["records"]}
    rows = []
    for question in dataset["questions"]:
        response = search_service.semantic_search(question["query"], top_k=20)
        before = response["results"]
        before_ids = [item["id"] for item in before]
        if len(before_ids) != len(set(before_ids)) or not set(before_ids) <= record_ids:
            raise ValueError(f'{question["id"]}: invalid retrieval candidate identity')
        if any(item.get("rank") != rank for rank, item in enumerate(before, 1)):
            # Gaps are valid when an indexed item has no mapping or DB record.
            ranks = [item.get("rank") for item in before]
            if (any(type(rank) is not int or rank < 1 for rank in ranks)
                    or ranks != sorted(set(ranks))):
                raise ValueError(f'{question["id"]}: invalid retrieval ranks')

        after = search_service.rerank_results(question["query"], before, top_k=len(before))
        after_ids = [item["id"] for item in after]
        if len(after_ids) != len(before_ids) or set(after_ids) != set(before_ids):
            raise ValueError(f'{question["id"]}: reranking changed the candidate set')
        executed = bool(before) and all("rerank_score" in item for item in after)
        if any("rerank_score" in item for item in after) and not executed:
            raise ValueError(f'{question["id"]}: partial reranking scores')
        if not executed and after_ids != before_ids:
            raise ValueError(f'{question["id"]}: changed order without reranking scores')

        relevance = {int(key): grade for key, grade in question["relevance"].items()}
        before_ndcg = ndcg_at_k(before_ids, relevance, 5)
        after_ndcg = ndcg_at_k(after_ids, relevance, 5)
        before_mrr = mrr_at_k(before_ids, relevance, 5)
        after_mrr = mrr_at_k(after_ids, relevance, 5)
        recall = recall_at_k(before_ids, relevance, 20, answerable=question["answerable"])
        missing_relevant_ids = sorted(set(question["relevant_ids"]) - set(before_ids))
        missing_evidence_ids = sorted(set(question["evidence_ids"]) - set(before_ids))
        delta = after_ndcg - before_ndcg
        outcome = "improved" if delta > 1e-12 else "regressed" if delta < -1e-12 else "unchanged"
        after_by_id = {item["id"]: item for item in after}
        candidates = []
        for item in before:
            reranked = after_by_id[item["id"]]
            candidates.append({
                "id": item["id"],
                "relevance": relevance.get(item["id"], 0),
                "retrieval_rank": item["rank"],
                "retrieval_score": item.get("similarity_score", item.get("keyword_score")),
                "retrieval_score_type": "similarity" if "similarity_score" in item else
                                        "keyword" if "keyword_score" in item else None,
                "reranked_rank": reranked["rank"] if executed else None,
                "rerank_score": reranked.get("rerank_score") if executed else None,
            })
        if question["answerable"] and recall < 1:
            classification = "retrieval_miss"
        elif response["search_type"] != "semantic":
            classification = "fallback"
        elif not executed:
            classification = "reranking_skipped"
        elif after_ndcg < 1 - 1e-12:
            classification = "reranking_weak"
        else:
            classification = "top5_ideal"
        reranking_state = ("executed" if executed else "no_candidates" if not before else
                           "skipped_unavailable" if getattr(search_service, "rerank_model", None) is None
                           else "failed")
        rows.append({
            "query_id": question["id"],
            "tags": question["tags"],
            "answerable": question["answerable"],
            "relevant_ids": question["relevant_ids"],
            "evidence_ids": question["evidence_ids"],
            "missing_relevant_ids": missing_relevant_ids,
            "missing_evidence_ids": missing_evidence_ids,
            "search_type": response["search_type"],
            "missing_mapping_ranks": response.get("missing_mapping_ranks", []),
            "missing_record_ranks": response.get("missing_record_ranks", []),
            "reranking_executed": executed,
            "reranking_state": reranking_state,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "recall_at_20": recall,
            "ndcg_at_5_before": before_ndcg,
            "ndcg_at_5_after": after_ndcg,
            "mrr_at_5_before": before_mrr,
            "mrr_at_5_after": after_mrr,
            "outcome": outcome,
            "classification": classification,
            "error": response.get("error"),
        })

    def mean(values):
        return sum(values) / len(values) if values else None

    recall_values = [row["recall_at_20"] for row in rows if row["recall_at_20"] is not None]
    summary = {
        "query_count": len(rows),
        "record_count": len(record_ids),
        "recall_denominator": len(recall_values),
        "recall_excluded_query_ids": [row["query_id"] for row in rows
                                      if row["recall_at_20"] is None],
        "recall_at_20": mean(recall_values),
        "ndcg_at_5_before": mean([row["ndcg_at_5_before"] for row in rows]),
        "ndcg_at_5_after": mean([row["ndcg_at_5_after"] for row in rows]),
        "mrr_at_5_before": mean([row["mrr_at_5_before"] for row in rows]),
        "mrr_at_5_after": mean([row["mrr_at_5_after"] for row in rows]),
        "improved": sum(row["outcome"] == "improved" for row in rows),
        "regressed": sum(row["outcome"] == "regressed" for row in rows),
        "unchanged": sum(row["outcome"] == "unchanged" for row in rows),
        "reranking_skipped": sum(not row["reranking_executed"] for row in rows),
        "fallback_query_ids": [row["query_id"] for row in rows
                               if row["search_type"] != "semantic"],
        "retrieval_miss_query_ids": [row["query_id"] for row in rows
                                     if row["classification"] == "retrieval_miss"],
        "evidence_miss_query_ids": [row["query_id"] for row in rows
                                    if row["missing_evidence_ids"]],
    }
    return {"summary": summary, "queries": rows}


def run_real_evaluation():
    """Build real embeddings and FAISS only inside D1's temporary storage."""
    from Backend.services import search_service as search_module
    from Backend.services import vector_service as vector_module

    dataset = load_dataset()
    with isolated_evaluation(dataset) as (app, paths):
        app.config["DATA_DIR"] = str(paths["root"])
        vector = vector_module.VectorService()
        if vector.embedding_model is None:
            raise RuntimeError("real embedding model is unavailable")
        # Manual KnowledgeItem ingestion calls add_document(id, content).
        texts = [record["content"] for record in dataset["records"]]
        ids = [record["id"] for record in dataset["records"]]
        if not vector.build_faiss_index(vector.batch_vectorize(texts), ids):
            raise RuntimeError("real FAISS index build failed")
        previous = vector_module.vector_service
        vector_module.vector_service = vector
        try:
            search = search_module.SearchService()
            if search.rerank_model is None:
                raise RuntimeError("real CrossEncoder reranker is unavailable")
            report = evaluate_questions(dataset, search)
        finally:
            vector_module.vector_service = previous
        report["metadata"] = {
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_version": dataset["version"],
            "dataset_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
            "embedding_model": app.config.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            "reranker_model": app.config.get("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            "mode": "WSL native, isolated temporary SQLite and FAISS, real local models",
            "candidate_k": 20,
            "ranking_k": 5,
            "document_text": "content only, matching manual KnowledgeItem ingestion; production embedding preprocessing applies",
            "rerank_text": "production semantic_search content (first 500 characters for long records)",
            "score_note": "FAISS inner product and raw CrossEncoder score are not comparable scales",
        }
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON report path outside the repository")
    args = parser.parse_args()
    report = run_real_evaluation()
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
