"""Deterministic D1 contracts in the existing backend CI boundary."""

from copy import deepcopy
from difflib import SequenceMatcher
import json
import math

import pytest

from Backend.evaluation.dataset import load_dataset, validate_dataset
from Backend.evaluation.loader import isolated_evaluation
from Backend.evaluation.metrics import recall_at_k, ndcg_at_k, mrr_at_k


pytestmark = pytest.mark.ci


def test_dataset_contract_and_boundary_coverage():
    data = load_dataset()
    assert len(data["records"]) == 24
    assert len(data["questions"]) == 30
    assert sum(q["answerable"] for q in data["questions"]) == 28
    assert sum(not q["answerable"] for q in data["questions"]) == 2
    assert sum("multi_document" in q["tags"] for q in data["questions"]) == 3
    assert sum("beyond_first_500" in q["tags"] and q["answerable"]
               for q in data["questions"]) >= 3
    assert {grade for q in data["questions"]
            for grade in q["relevance"].values()} == {0, 1, 2}
    assert all(q["expected_facts"] and q["evidence_ids"] for q in data["questions"]
               if q["answerable"])


def test_repaired_question_ground_truth_and_distinct_late_evidence():
    data = load_dataset()
    records = {record["id"]: record for record in data["records"]}
    questions = {question["id"]: question for question in data["questions"]}

    first = questions["Q001"]
    assert [fact["text"] for fact in first["expected_facts"]] == ["末班时间为23时30分"]
    assert first["expected_facts"][0]["evidence"][0]["quote"] == "运行至23时30分"
    assert first["relevance"]["1001"] == 2

    residential = questions["Q030"]
    assert residential["answerable"] is True
    assert residential["refusal_reason"] is None
    assert residential["relevance"] == {"1007": 2, "1008": 0}
    assert residential["expected_facts"][0]["text"] == "本轮节水阀覆盖居民住宅0户"
    assert residential["evidence_ids"] == [1007]
    assert residential["expected_facts"][0]["evidence"][0]["start"] > 500

    long_cases = [("Q007", 1007), ("Q015", 1015), ("Q023", 1023)]
    for qid, record_id in long_cases:
        question = questions[qid]
        span = question["expected_facts"][0]["evidence"][0]
        assert span["record_id"] == record_id
        assert span["start"] > 500
        assert records[record_id]["content"][span["start"]:span["end"]] == span["quote"]
        assert question["relevance"][str(record_id)] == 2

    contents = [records[record_id]["content"] for _, record_id in long_cases]
    for left in range(len(contents)):
        for right in range(left + 1, len(contents)):
            match = SequenceMatcher(None, contents[left], contents[right],
                                    autojunk=False).find_longest_match()
            assert match.size < 80


@pytest.mark.parametrize("change", [
    lambda d: d["records"][1].update(id=d["records"][0]["id"]),
    lambda d: d["questions"][1].update(id=d["questions"][0]["id"]),
    lambda d: d["questions"][0]["relevance"].update({"9999": 2}),
    lambda d: d["questions"][0]["relevance"].update({"1001": 3}),
    lambda d: d["questions"][0].update(relevant_ids=[]),
    lambda d: d["questions"][0]["expected_facts"][0].update(text=""),
    lambda d: d["questions"][0]["expected_facts"][0]["evidence"][0].update(start=9999),
    lambda d: d["questions"][0]["expected_facts"][0]["evidence"][0].update(record_id=1002),
    lambda d: d["questions"][0].update(evidence_ids=[9999]),
    lambda d: d["questions"][27].update(expected_facts=[{"text": "bad", "evidence": []}]),
    lambda d: d["questions"][27].update(refusal_reason=None),
    lambda d: d["questions"][0].update(answerable="yes"),
    lambda d: d["questions"][0].update(tags=["no_answer"]),
    lambda d: d["questions"][6]["expected_facts"][0]["evidence"][0].update(start=100),
])
def test_validator_rejects_invalid_ground_truth(change):
    data = deepcopy(load_dataset())
    change(data)
    with pytest.raises(ValueError):
        validate_dataset(data)


def test_validator_rejects_missing_scenario_and_changed_quote():
    data = load_dataset()
    for question in data["questions"]:
        question["tags"] = [tag for tag in question["tags"]
                            if tag != "truncation_sensitive"]
    with pytest.raises(ValueError, match="missing required scenarios"):
        validate_dataset(data)
    data = load_dataset()
    data["questions"][0]["expected_facts"][0]["evidence"][0]["quote"] = "wrong quote"
    with pytest.raises(ValueError, match="invalid evidence position"):
        validate_dataset(data)


def test_recall_cutoff_and_no_answer_contract():
    labels = {1: 2, 2: 1, 3: 0}
    assert recall_at_k([], labels, 5, answerable=True) == 0
    assert recall_at_k([3, 1], labels, 1, answerable=True) == 0
    assert recall_at_k([3, 1], labels, 5, answerable=True) == 0.5
    assert recall_at_k(list(range(4, 23)) + [1], labels, 20, answerable=True) == 0.5
    assert recall_at_k([1], {}, 20, answerable=True) is None
    assert recall_at_k([2], {2: 1}, 20, answerable=False) is None
    no_answer = load_dataset()["questions"][27]
    labels = {int(key): grade for key, grade in no_answer["relevance"].items()}
    assert recall_at_k([1010], labels, 20,
                       answerable=no_answer["answerable"]) is None


def test_ndcg_graded_gain_and_zero_ideal():
    labels = {1: 2, 2: 1}
    assert ndcg_at_k([1, 2], labels, 5) == 1
    expected = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))
    assert ndcg_at_k([2, 1], labels, 5) == pytest.approx(expected)
    assert ndcg_at_k([], labels, 5) == 0
    assert ndcg_at_k([1], {1: 0}, 20) == 0
    assert ndcg_at_k([3, 1], labels, 1) == 0


def test_mrr_rank_boundaries_and_empty():
    assert mrr_at_k([1], {1: 2}, 5) == 1
    assert mrr_at_k([0, 1], {1: 1}, 5) == 0.5
    assert mrr_at_k([2, 3, 4, 5, 1], {1: 2}, 5) == 0.2
    assert mrr_at_k([2, 3, 4, 5, 1], {1: 2}, 4) == 0
    assert mrr_at_k([], {1: 2}, 20) == 0


@pytest.mark.parametrize("metric,kwargs", [
    (recall_at_k, {"answerable": True}), (ndcg_at_k, {}), (mrr_at_k, {}),
])
def test_metrics_reject_duplicate_ids_and_invalid_cutoff(metric, kwargs):
    with pytest.raises(ValueError, match="unique"):
        metric([1, 1], {1: 2}, 5, **kwargs)
    with pytest.raises(ValueError, match="positive"):
        metric([1], {1: 2}, 0, **kwargs)


def test_loader_uses_only_temporary_storage_and_cleans_up(monkeypatch, tmp_path):
    from Backend.models import KnowledgeItem, db
    import faiss
    personal_db = tmp_path / "personal.sqlite"
    personal_index = tmp_path / "personal.index"
    personal_db.write_bytes(b"personal db sentinel")
    personal_index.write_bytes(b"personal index sentinel")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{personal_db}")
    monkeypatch.setenv("FAISS_INDEX_PATH", str(personal_index))
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "personal-data"))
    expected_content = load_dataset()["records"][0]["content"]
    for _ in range(2):
        with isolated_evaluation() as (app, paths):
            assert app.config["SQLALCHEMY_DATABASE_URI"] == f"sqlite:///{paths['database']}"
            assert paths["database"] != personal_db
            assert paths["index"] != personal_index
            assert paths["database"].is_relative_to(paths["root"])
            assert db.session.query(KnowledgeItem).count() == 24
            assert [item.id for item in db.session.query(KnowledgeItem).order_by(KnowledgeItem.id)] == list(range(1001, 1025))
            assert db.session.get(KnowledgeItem, 1001).content == expected_content
            assert faiss.read_index(str(paths["index"])).ntotal == 0
            assert json.loads(paths["mapping"].read_text()) == {}
            root = paths["root"]
        assert not root.exists()
    assert personal_db.read_bytes() == b"personal db sentinel"
    assert personal_index.read_bytes() == b"personal index sentinel"
    assert not (tmp_path / "personal-data").exists()
