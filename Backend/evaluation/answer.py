"""D3 answer evidence cues and review records; no automatic semantic verdicts."""

from collections import Counter
import re

from .dataset import validate_dataset


RUBRIC_AXES = ("factual_correctness", "completeness", "grounding", "refusal_correctness")
REFUSAL_CUES = ("无法确定", "无法回答", "未提供", "没有提供", "未公布", "没有公布",
                "未说明", "没有说明", "信息不足", "资料不足", "不足以", "无法得知", "不知道")
ANCHOR_RE = re.compile(r"\d+(?:时\d+分|点\d+分|万|千|百|个|台|盏|人|户|秒|天|次|处|公斤|千瓦时)?|[零一二三四五六七八九十百千万两]+(?:时|点|分|个|台|盏|人|户|秒|天|次|处|公斤|千瓦时)|周[一二三四五六日天]")
CHINESE_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9}


def anchor_present(token, answer):
    if re.search(r"(?<!\d)" + re.escape(token) + r"(?!\d)", answer):
        return True
    match = re.fullmatch(r"([零一二两三四五六七八九十]+)(.*)", token)
    if not match:
        return False
    number, suffix = match.groups()
    if number == "十":
        value = 10
    elif "十" in number:
        tens, ones = number.split("十", 1)
        if (tens and tens not in CHINESE_DIGITS) or (ones and ones not in CHINESE_DIGITS):
            return False
        value = (CHINESE_DIGITS[tens] if tens else 1) * 10 + (CHINESE_DIGITS[ones] if ones else 0)
    elif number in CHINESE_DIGITS:
        value = CHINESE_DIGITS[number]
    else:
        return False
    return bool(re.search(r"(?<!\d)" + str(value) + re.escape(suffix) + r"(?!\d)", answer))


def evidence_cues(question, answer, candidate_ids, context):
    """Return reproducible literal cues, never a factual or grounding grade."""
    expected_ids = set(question["evidence_ids"])
    candidate_ids = set(candidate_ids)
    context_by_id = {item["id"]: item.get("content", "") for item in context}
    if len(context_by_id) != len(context):
        raise ValueError("duplicate context ID")
    fact_cues = []
    for fact in question["expected_facts"]:
        anchors = sorted(set(ANCHOR_RE.findall(fact["text"])))
        fact_cues.append({
            "fact": fact["text"],
            "literal_fact_present": fact["text"] in answer,
            "anchors": [{"text": token, "present": anchor_present(token, answer)}
                        for token in anchors],
            "visible_span_ids": sorted({span["record_id"] for span in fact["evidence"]
                                        if span["quote"] in context_by_id.get(span["record_id"], "")}),
        })
    return {
        "missing_candidate_evidence_ids": sorted(expected_ids - candidate_ids),
        "missing_context_evidence_ids": sorted(expected_ids - context_by_id.keys()),
        "context_evidence_ids": sorted(expected_ids & context_by_id.keys()),
        "fact_cues": fact_cues,
        "refusal_cue_present": any(cue in answer for cue in REFUSAL_CUES),
        "refusal_cue_matches": [cue for cue in REFUSAL_CUES if cue in answer],
    }


def classify(question, cues):
    """Classify only cases established by visibility or explicit lexical cues."""
    if question["answerable"]:
        if cues["missing_candidate_evidence_ids"] or cues["missing_context_evidence_ids"] or any(
            not fact["visible_span_ids"] for fact in cues["fact_cues"]
        ):
            return "retrieval_limited"
        # A response may correctly answer and then say that *other* details are
        # unspecified. Treat a refusal cue as a candidate only when no expected
        # literal fact or numeric/date anchor appears in the answer.
        answered_cue = any(fact["literal_fact_present"] or any(
            anchor["present"] for anchor in fact["anchors"]
        ) for fact in cues["fact_cues"])
        if cues["refusal_cue_present"] and not answered_cue:
            return "generation_limited_candidate"
        return "ambiguous_human_review"
    if cues["refusal_cue_present"]:
        return "correct_refusal_candidate"
    return "ambiguous_human_review"


def score_result(question, answer, candidate_ids, context, *, run_id, attempt, timestamp):
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("missing or malformed generated answer")
    if not isinstance(run_id, str) or not run_id or type(attempt) is not int or attempt < 1:
        raise ValueError("invalid run identity")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("missing timestamp")
    cues = evidence_cues(question, answer, candidate_ids, context)
    classification = classify(question, cues)
    return {
        "query_id": question["id"], "tags": question["tags"],
        "answerable": question["answerable"], "query": question["query"],
        "expected_facts": question["expected_facts"],
        "expected_evidence_ids": question["evidence_ids"],
        "refusal_reason": question["refusal_reason"],
        "retrieved_evidence_ids": sorted(set(candidate_ids) & set(question["evidence_ids"])),
        "candidate_ids": list(candidate_ids),
        "context_ids": [item["id"] for item in context],
        "context": context,
        "answer": answer, "rules": cues, "classification": classification,
        "rubric": {axis: {"score": None, "reviewer": None, "rationale": None}
                   for axis in RUBRIC_AXES},
        "manual_review": {
            "state": "pending", "reason": "D1 rubric requires semantic and unsupported-claim review",
            "question": "按 D1 四轴 0/1/2 rubric，核查事实、遗漏、所有实质性主张的依据及拒答原因；逐项记录证据与理由。",
        },
        "run_id": run_id, "attempt": attempt, "timestamp_utc": timestamp,
    }


def validate_report(report, dataset):
    validate_dataset(dataset)
    questions = {q["id"]: q for q in dataset["questions"]}
    first = report.get("authoritative", [])
    if len(first) != len(questions) or {r.get("query_id") for r in first} != set(questions):
        raise ValueError("authoritative baseline must have exactly one result per question")
    if any(r.get("attempt") != 1 or r.get("manual_review", {}).get("state") != "pending"
           for r in first):
        raise ValueError("invalid authoritative attempt or review state")
    selected = report.get("repeatability_selection", {})
    if not selected or not set(selected) <= set(questions):
        raise ValueError("invalid repeatability selection")
    repeats = report.get("repeatability", [])
    counts = Counter(r.get("query_id") for r in repeats)
    if any(counts[qid] != 2 for qid in selected) or set(counts) != set(selected):
        raise ValueError("each selected question needs exactly two additional runs")
    for qid in selected:
        if sorted(r.get("attempt") for r in repeats if r.get("query_id") == qid) != [2, 3]:
            raise ValueError("invalid repeated attempt numbers")
    for row in first + repeats:
        if row.get("run_id") != report.get("metadata", {}).get("run_id"):
            raise ValueError("run ID mismatch")
        if not isinstance(row.get("answer"), str) or not row["answer"].strip():
            raise ValueError("missing answer")
        if row.get("expected_evidence_ids") != questions[row["query_id"]]["evidence_ids"]:
            raise ValueError("evidence mapping mismatch")
        if row.get("expected_facts") != questions[row["query_id"]]["expected_facts"]:
            raise ValueError("expected facts mapping mismatch")
    return True


def summarize(report):
    rows = report["authoritative"]
    return {
        "questions": len(rows),
        "answerable": sum(r["answerable"] for r in rows),
        "unanswerable": sum(not r["answerable"] for r in rows),
        "classifications": dict(Counter(r["classification"] for r in rows)),
        "rubric_pending": {axis: sum(r["rubric"][axis]["score"] is None for r in rows)
                           for axis in RUBRIC_AXES},
        "review_queue_count": sum(r["manual_review"]["state"] == "pending" for r in rows),
        "repeatability_questions": len(report["repeatability_selection"]),
        "additional_runs": len(report["repeatability"]),
    }


def build_review_queue(report):
    """Keep every semantic judgement visible for the D1 human rubric."""
    return [{
        "query_id": row["query_id"], "scenario": row["tags"],
        "answer": row["answer"],
        "expected_facts": [fact["text"] for fact in row["expected_facts"]],
        "expected_evidence_ids": row["expected_evidence_ids"],
        "refusal_reason": row["refusal_reason"],
        "deterministic_result": row["rules"],
        "classification": row["classification"],
        "review_reason": row["manual_review"]["reason"],
        "rubric_question": row["manual_review"]["question"],
        "state": row["manual_review"]["state"],
    } for row in report["authoritative"]]


def compare_repeatability(report):
    """Describe exact and deterministic changes, without averaging or judging."""
    first = {row["query_id"]: row for row in report["authoritative"]}
    comparisons = []
    for qid in report["repeatability_selection"]:
        rows = [first[qid]] + sorted(
            (row for row in report["repeatability"] if row["query_id"] == qid),
            key=lambda row: row["attempt"])
        comparisons.append({
            "query_id": qid,
            "selection_reason": report["repeatability_selection"][qid],
            "answers": [{"attempt": row["attempt"], "answer": row["answer"],
                         "classification": row["classification"], "rules": row["rules"]}
                        for row in rows],
            "generation_text_varies": len({row["answer"] for row in rows}) > 1,
            "retrieval_candidate_ids_vary": len({tuple(row["candidate_ids"]) for row in rows}) > 1,
            "context_ids_vary": len({tuple(row["context_ids"]) for row in rows}) > 1,
            "deterministic_rules_vary": len({repr(row["rules"]) for row in rows}) > 1,
            "human_review_disagreement": "pending review",
            "interpretation": "descriptive only; not statistically significant",
        })
    return comparisons
