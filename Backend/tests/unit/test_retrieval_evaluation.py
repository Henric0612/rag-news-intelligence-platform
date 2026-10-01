"""Deterministic D2 identity, score, state, and metric contracts."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import faiss

from Backend.evaluation.dataset import load_dataset
from Backend.evaluation.loader import isolated_evaluation
from Backend.evaluation.retrieval import evaluate_questions
from Backend.services.search_service import SearchService
from Backend.services.vector_service import VectorService


pytestmark = pytest.mark.ci


def search_service(vector, reranker=None):
    service = SearchService.__new__(SearchService)
    service.vector_service = vector
    service.rerank_model = reranker
    service.cache_enabled = False
    return service


@pytest.mark.parametrize("ids,missing_field", [
    ([1001, -1, 1002], "missing_mapping_ranks"),
    ([1001, 9999, 1002], "missing_record_ranks"),
])
def test_semantic_scores_and_ranks_stay_with_faiss_ids(ids, missing_field):
    vector = SimpleNamespace(
        embedding_model=object(), faiss_index=object(), id_mapping={0: 1001},
        vectorize_text=lambda query: np.zeros(384),
        search_similar=lambda query, top_k: (np.array([0.95, 0.90, 0.80]), ids),
    )
    with isolated_evaluation() as (app, _):
        response = search_service(vector).semantic_search("东站", top_k=3)
    assert response["search_type"] == "semantic"
    assert [(item["id"], item["rank"], item["similarity_score"])
            for item in response["results"]] == [(1001, 1, 0.95), (1002, 3, 0.80)]
    assert response[missing_field] == [2]


def test_faiss_search_exposes_unmapped_positions_without_shifting_scores():
    service = VectorService.__new__(VectorService)
    service.faiss_index = faiss.IndexFlatIP(384)
    vectors = np.zeros((3, 384), dtype="float32")
    vectors[:, 0] = [1.0, 0.8, 0.6]
    service.faiss_index.add(vectors)
    service.id_mapping = {0: 1001, 2: 1002}
    scores, ids = service.search_similar(vectors[0], top_k=3)
    assert ids == [1001, -1, 1002]
    assert scores.tolist() == pytest.approx([1.0, 0.8, 0.6])


def test_real_reranker_scores_are_attached_to_their_candidate():
    scorer = Mock()
    scorer.score.return_value = [0.12, -0.63, 0.78]
    service = search_service(None, SimpleNamespace(model=scorer))
    before = [
        {"id": 1001, "rank": 1, "content": "first", "similarity_score": 0.8},
        {"id": 1002, "rank": 2, "content": "second", "similarity_score": 0.7},
        {"id": 1003, "rank": 3, "content": "third", "similarity_score": 0.6},
    ]
    after = service.rerank_results("query", before, top_k=3)
    assert [(item["id"], item["rank"], item["rerank_score"])
            for item in after] == [(1003, 1, 0.78), (1001, 2, 0.12), (1002, 3, -0.63)]
    assert [item["rank"] for item in before] == [1, 2, 3]


def test_skipped_reranker_has_no_invented_score():
    service = search_service(None)
    before = [{"id": 1001, "rank": 1, "content": "first"}]
    assert service.rerank_results("query", before) == before
    assert "rerank_score" not in before[0]


class FakeSearch:
    def __init__(self, *, search_type="semantic", rerank=True, changed_set=False):
        self.search_type = search_type
        self.rerank = rerank
        self.changed_set = changed_set
        self.rerank_model = object() if rerank else None

    def semantic_search(self, query, top_k):
        return {
            "search_type": self.search_type,
            "results": [
                {"id": 1002, "rank": 1, "keyword_score": 1.0},
                {"id": 1001, "rank": 2, "similarity_score": 0.6},
            ],
            "missing_mapping_ranks": [3],
        }

    def rerank_results(self, query, results, top_k):
        if self.changed_set:
            return [{"id": 1001, "rank": 1, "rerank_score": 3.0}]
        if not self.rerank:
            return results[:top_k]
        return [{**results[1], "rank": 1, "rerank_score": 3.0},
                {**results[0], "rank": 2, "rerank_score": -2.0}]


def two_question_dataset():
    data = load_dataset()
    data["questions"] = [deepcopy(data["questions"][0]), deepcopy(data["questions"][27])]
    return data


def test_report_metrics_trace_and_no_answer_denominator():
    report = evaluate_questions(two_question_dataset(), FakeSearch())
    first = report["queries"][0]
    assert report["summary"]["recall_denominator"] == 1
    assert report["summary"]["recall_excluded_query_ids"] == ["Q028"]
    assert report["summary"]["recall_at_20"] == 1.0
    assert first["reranking_executed"] is True
    assert first["outcome"] == "improved"
    assert first["candidates"][1] == {
        "id": 1001, "relevance": 2, "retrieval_rank": 2,
        "retrieval_score": 0.6, "retrieval_score_type": "similarity",
        "reranked_rank": 1, "rerank_score": 3.0,
    }
    assert first["missing_mapping_ranks"] == [3]


def test_report_distinguishes_fallback_and_reranking_skip():
    report = evaluate_questions(two_question_dataset(), FakeSearch(search_type="keyword_fallback", rerank=False))
    assert report["summary"]["fallback_query_ids"] == ["Q001", "Q028"]
    assert report["summary"]["reranking_skipped"] == 2
    assert all(row["reranking_state"] == "skipped_unavailable" for row in report["queries"])
    assert all(candidate["rerank_score"] is None for row in report["queries"]
               for candidate in row["candidates"])


def test_report_rejects_candidate_set_change():
    with pytest.raises(ValueError, match="candidate set"):
        evaluate_questions(two_question_dataset(), FakeSearch(changed_set=True))


def test_report_distinguishes_failed_reranker_from_unavailable():
    service = FakeSearch()
    service.rerank_results = lambda query, results, top_k: results[:top_k]
    report = evaluate_questions(two_question_dataset(), service)
    assert all(row["reranking_state"] == "failed" for row in report["queries"])
    assert report["summary"]["reranking_skipped"] == 2
