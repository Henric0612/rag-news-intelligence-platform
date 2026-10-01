"""Load and validate the fixed v1 evaluation dataset without application imports."""

import json
from pathlib import Path


DATASET_PATH = Path(__file__).with_name("golden_v1.json")
REQUIRED_SCENARIOS = {
    "single_document", "multi_document", "similar_records", "confusing_facts",
    "answerable", "no_answer", "long_content", "evidence_early",
    "evidence_late", "beyond_first_500", "truncation_sensitive",
    "ambiguous_candidates",
}


def load_dataset(path=DATASET_PATH):
    """Return the parsed dataset after checking every reference and evidence offset."""
    with Path(path).open(encoding="utf-8") as stream:
        dataset = json.load(stream)
    validate_dataset(dataset)
    return dataset


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def validate_dataset(dataset):
    """Raise ValueError for malformed schema or inconsistent ground truth."""
    _check(isinstance(dataset, dict) and dataset.get("version") == "v1", "version must be v1")
    records = dataset.get("records")
    questions = dataset.get("questions")
    _check(isinstance(records, list) and bool(records), "records must be nonempty")
    _check(isinstance(questions, list) and bool(questions), "questions must be nonempty")
    by_id = {}
    for record in records:
        _check(isinstance(record, dict), "record must be an object")
        record_id = record.get("id")
        _check(type(record_id) is int and record_id > 0 and record_id not in by_id,
               "record IDs must be unique positive integers")
        for field in ("title", "content", "category"):
            _check(isinstance(record.get(field), str) and bool(record[field].strip()),
                   f"record {record_id}: invalid {field}")
        by_id[record_id] = record

    seen_questions = set()
    scenarios = set()
    for question in questions:
        _check(isinstance(question, dict), "question must be an object")
        qid = question.get("id")
        _check(isinstance(qid, str) and bool(qid) and qid not in seen_questions,
               "question IDs must be unique nonempty strings")
        seen_questions.add(qid)
        _check(isinstance(question.get("query"), str) and bool(question["query"].strip()),
               f"{qid}: missing query")
        tags = question.get("tags")
        _check(isinstance(tags, list) and bool(tags) and
               all(isinstance(tag, str) and bool(tag) for tag in tags) and
               len(tags) == len(set(tags)), f"{qid}: invalid tags")
        scenarios.update(tags)
        answerable = question.get("answerable")
        _check(type(answerable) is bool, f"{qid}: answerable must be boolean")
        _check(("answerable" if answerable else "no_answer") in tags,
               f"{qid}: answerability tag mismatch")
        _check(not ({"answerable", "no_answer"} <= set(tags)),
               f"{qid}: contradictory answerability tags")
        labels = question.get("relevance")
        _check(isinstance(labels, dict) and bool(labels), f"{qid}: missing relevance")
        for raw_id, grade in labels.items():
            _check(isinstance(raw_id, str) and raw_id.isdecimal() and
                   int(raw_id) in by_id, f"{qid}: dangling relevance ID")
            _check(type(grade) is int and grade in (0, 1, 2), f"{qid}: invalid grade")
        relevant = {int(key) for key, grade in labels.items() if grade > 0}
        _check(question.get("relevant_ids") == sorted(relevant),
               f"{qid}: relevant_ids must match grades 1 and 2")
        facts = question.get("expected_facts")
        evidence_ids = question.get("evidence_ids")
        _check(isinstance(facts, list) and isinstance(evidence_ids, list) and
               len(evidence_ids) == len(set(evidence_ids)), f"{qid}: invalid facts/evidence IDs")
        actual_evidence = set()
        for fact in facts:
            _check(isinstance(fact, dict) and isinstance(fact.get("text"), str) and
                   bool(fact["text"].strip()) and isinstance(fact.get("evidence"), list) and
                   bool(fact["evidence"]), f"{qid}: invalid expected fact")
            for span in fact["evidence"]:
                _check(isinstance(span, dict), f"{qid}: invalid evidence span")
                rid, start, end, quote = (span.get(key) for key in
                                          ("record_id", "start", "end", "quote"))
                _check(type(rid) is int and rid in by_id, f"{qid}: dangling evidence ID")
                content = by_id[rid]["content"]
                _check(type(start) is int and type(end) is int and
                       0 <= start < end <= len(content) and
                       isinstance(quote, str) and bool(quote) and
                       content[start:end] == quote, f"{qid}: invalid evidence position")
                _check(labels.get(str(rid)) == 2,
                       f"{qid}: evidence requires directly relevant label 2")
                actual_evidence.add(rid)
        _check(evidence_ids == sorted(actual_evidence), f"{qid}: evidence_ids mismatch")
        if "single_document" in tags:
            _check(len(evidence_ids) == 1, f"{qid}: single-document evidence mismatch")
        if "multi_document" in tags:
            _check(len(evidence_ids) >= 2, f"{qid}: multi-document evidence mismatch")
        if "beyond_first_500" in tags and answerable:
            _check(any(span["start"] >= 500 for fact in facts
                       for span in fact["evidence"]), f"{qid}: evidence is not beyond 500")
        if "evidence_early" in tags:
            _check(any(span["start"] < 500 for fact in facts
                       for span in fact["evidence"]), f"{qid}: no early evidence")
        if "evidence_late" in tags:
            _check(any(span["start"] >= len(by_id[span["record_id"]]["content"]) // 2
                       for fact in facts for span in fact["evidence"]),
                   f"{qid}: no late evidence")
        if "long_content" in tags:
            _check(any(len(by_id[rid]["content"]) > 500 for rid in relevant),
                   f"{qid}: no long relevant record")
        if "ambiguous_candidates" in tags:
            _check(any(grade == 1 for grade in labels.values()) and len(labels) >= 2,
                   f"{qid}: no ambiguous partial candidate")
        reason = question.get("refusal_reason")
        if answerable:
            _check(bool(facts) and bool(evidence_ids) and reason is None and
                   any(grade == 2 for grade in labels.values()),
                   f"{qid}: inconsistent answerable ground truth")
        else:
            _check(not facts and not evidence_ids and
                   isinstance(reason, str) and bool(reason.strip()) and
                   all(grade < 2 for grade in labels.values()),
                   f"{qid}: inconsistent no-answer ground truth")
    _check(REQUIRED_SCENARIOS <= scenarios,
           f"missing required scenarios: {sorted(REQUIRED_SCENARIOS - scenarios)}")
