"""D3 deterministic report and evidence contracts; no real model calls."""

from copy import deepcopy
import json

import pytest

from Backend.evaluation.answer import (anchor_present, build_review_queue, compare_repeatability,
                                       score_result, summarize, validate_report)
from Backend.evaluation.answer_run import PRESELECTED, run_one
from Backend.evaluation.answer_report import make_package
from Backend.evaluation.dataset import load_dataset


pytestmark = pytest.mark.ci


def question(qid):
    return next(q for q in load_dataset()["questions"] if q["id"] == qid)


def test_visible_evidence_and_literal_number_cue_are_not_rubric_grades():
    q = question("Q001")
    content = q["expected_facts"][0]["evidence"][0]["quote"]
    row = score_result(q, "末班时间为23时30分。", [1001],
                       [{"id": 1001, "content": content}], run_id="run", attempt=1,
                       timestamp="2026-01-01T00:00:00Z")
    assert row["rules"]["fact_cues"][0]["visible_span_ids"] == [1001]
    assert row["rules"]["fact_cues"][0]["anchors"][0]["present"] is True
    assert row["classification"] == "ambiguous_human_review"
    assert all(axis["score"] is None for axis in row["rubric"].values())
    assert row["manual_review"]["state"] == "pending"


def test_number_and_date_anchors_are_deterministic_cues_only():
    assert anchor_present("十二个", "采样点增加到12个")
    assert anchor_present("两台", "验收2台储能柜")
    assert anchor_present("周二", "每周二下午")
    assert not anchor_present("8", "受理到18时")
    assert not anchor_present("周二", "每周三下午")


def test_missing_candidate_and_truncated_evidence_are_retrieval_limited():
    q = question("Q007")
    missing = score_result(q, "资料不足。", [], [], run_id="run", attempt=1, timestamp="t")
    truncated = score_result(q, "答案146个。", [1007],
                             [{"id": 1007, "content": "前500字不含证据"}],
                             run_id="run", attempt=1, timestamp="t")
    assert missing["rules"]["missing_candidate_evidence_ids"] == [1007]
    assert missing["classification"] == "retrieval_limited"
    assert truncated["rules"]["missing_context_evidence_ids"] == []
    assert truncated["classification"] == "retrieval_limited"


def test_answerable_refusal_and_no_answer_states():
    answerable = question("Q001")
    quote = answerable["expected_facts"][0]["evidence"][0]["quote"]
    refused = score_result(answerable, "资料不足，无法确定。", [1001],
                           [{"id": 1001, "content": quote}], run_id="run", attempt=1,
                           timestamp="t")
    no_answer = question("Q028")
    correct = score_result(no_answer, "公告未公布实际放电量。", [1010], [],
                           run_id="run", attempt=1, timestamp="t")
    invented = score_result(no_answer, "实际放电量是18万千瓦时。", [1010], [],
                            run_id="run", attempt=1, timestamp="t")
    assert refused["classification"] == "generation_limited_candidate"
    assert correct["classification"] == "correct_refusal_candidate"
    assert invented["classification"] == "ambiguous_human_review"
    assert correct["rubric"]["refusal_correctness"]["score"] is None
    answered_with_qualification = score_result(
        answerable, "末班时间为23时30分，其他调整信息未提供。", [1001],
        [{"id": 1001, "content": quote}], run_id="run", attempt=1, timestamp="t")
    assert answered_with_qualification["rules"]["refusal_cue_present"] is True
    assert answered_with_qualification["classification"] == "ambiguous_human_review"


def test_run_one_uses_actual_rag_method_and_preserves_trace():
    class FakeSearch:
        def semantic_search(self, query, top_k, filters, user_id):
            return {"search_type": "semantic", "results": [{"id": 1001, "rank": 1,
                     "content": "运行至23时30分", "title": "东站"}]}

        def rerank_results(self, query, results, top_k):
            return [{**results[0], "rerank_score": 2.0}]

    class FakeRag:
        rerank_top_k = 5
        search_service = FakeSearch()

        def answer_question(self, query):
            searched = self.search_service.semantic_search(query, 20, None, None)
            ranked = self.search_service.rerank_results(query, searched["results"], 5)
            return {"answer": "末班时间为23时30分。", "sources": ranked,
                    "model": "fake", "response_time": 1.0}

        def build_context(self, sources):
            return [{"id": s["id"], "content": s["content"]} for s in sources]

    rag = FakeRag()
    row = run_one(rag, question("Q001"), run_id="run", attempt=1)
    assert row["candidate_ids"] == [1001]
    assert row["reranking_trace"][0]["rerank_score"] == 2.0
    assert isinstance(rag.search_service, FakeSearch)


def test_report_identity_mapping_aggregation_and_repeat_bookkeeping():
    data = load_dataset()
    run_id = "d3-contract"
    rows = [score_result(q, "资料不足，无法确定。", [], [], run_id=run_id,
                         attempt=1, timestamp="t") for q in data["questions"]]
    repeats = [score_result(next(q for q in data["questions"] if q["id"] == qid),
                            "资料不足，无法确定。", [], [], run_id=run_id,
                            attempt=attempt, timestamp="t")
               for qid in PRESELECTED for attempt in (2, 3)]
    report = {"metadata": {"run_id": run_id}, "authoritative": rows,
              "repeatability_selection": PRESELECTED, "repeatability": repeats}
    assert validate_report(report, data)
    summary = summarize(report)
    assert summary["questions"] == 30
    assert summary["answerable"] == 28
    assert summary["unanswerable"] == 2
    assert summary["additional_runs"] == 12
    assert summary["rubric_pending"]["grounding"] == 30
    assert len(build_review_queue(report)) == 30
    assert build_review_queue(report)[0]["state"] == "pending"
    comparison = compare_repeatability(report)
    assert len(comparison) == len(PRESELECTED)
    assert all(len(case["answers"]) == 3 for case in comparison)
    assert all(case["human_review_disagreement"] == "pending review" for case in comparison)
    bad = deepcopy(report)
    bad["repeatability"].pop()
    with pytest.raises(ValueError, match="two additional runs"):
        validate_report(bad, data)
    bad = deepcopy(report)
    bad["authoritative"][0]["answer"] = ""
    with pytest.raises(ValueError, match="missing answer"):
        validate_report(bad, data)
    bad = deepcopy(report)
    bad["authoritative"][0]["expected_evidence_ids"] = []
    with pytest.raises(ValueError, match="evidence mapping"):
        validate_report(bad, data)
    bad = deepcopy(report)
    bad["authoritative"][0]["expected_facts"] = []
    with pytest.raises(ValueError, match="expected facts mapping"):
        validate_report(bad, data)


def test_review_package_preserves_authoritative_answers(tmp_path):
    data = load_dataset()
    rows = [score_result(q, "资料不足，无法确定。", [], [], run_id="run",
                         attempt=1, timestamp="t") for q in data["questions"]]
    repeats = [score_result(next(q for q in data["questions"] if q["id"] == qid),
                            "资料不足，无法确定。", [], [], run_id="run",
                            attempt=attempt, timestamp="t")
               for qid in PRESELECTED for attempt in (2, 3)]
    source = tmp_path / "baseline.json"
    original = {"metadata": {"run_id": "run", "runtime_mode": "fixture",
                             "generation_explicit": {"temperature": 0.7}},
                "authoritative": rows, "repeatability_selection": PRESELECTED,
                "repeatability": repeats}
    source.write_text(json.dumps(original), encoding="utf-8")
    package = make_package(source)
    assert json.loads(source.read_text()) == original
    scored = json.loads(open(package["scored_baseline"], encoding="utf-8").read())
    assert [r["answer"] for r in scored["authoritative"]] == [r["answer"] for r in rows]
    assert scored["authoritative"][0]["runtime_mode"] == "fixture"
    assert len(json.loads(open(package["review_queue"], encoding="utf-8").read())["queue"]) == 30
    assert "Q030" in open(package["human_review"], encoding="utf-8").read()


def test_malformed_result_rejected():
    with pytest.raises(ValueError, match="answer"):
        score_result(question("Q001"), None, [], [], run_id="r", attempt=1, timestamp="t")
