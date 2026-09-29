"""Validate a completed D3 baseline and produce review and repeatability files."""

import argparse
import json
from pathlib import Path

from .answer import (build_review_queue, classify, compare_repeatability,
                     evidence_cues, summarize, validate_report)
from .dataset import load_dataset


def make_package(baseline_path):
    path = Path(baseline_path).resolve()
    repo = Path(__file__).resolve().parents[2]
    if path == repo or repo in path.parents:
        raise ValueError("review artifacts must be outside the repository")
    report = json.loads(path.read_text(encoding="utf-8"))
    dataset = load_dataset()
    validate_report(report, dataset)
    questions = {q["id"]: q for q in dataset["questions"]}
    for row in report["authoritative"] + report["repeatability"]:
        cues = evidence_cues(questions[row["query_id"]], row["answer"],
                             row["candidate_ids"], row["context"])
        row["rules"] = cues
        row["classification"] = classify(questions[row["query_id"]], cues)
        row["generation_configuration"] = report["metadata"].get("generation_explicit")
        row["runtime_mode"] = report["metadata"].get("runtime_mode")
    report["metadata"]["scoring_revision"] = "D3 deterministic cues v3; answers and retrieval traces copied unchanged"
    report["metadata"]["source_baseline"] = str(path)
    validate_report(report, dataset)
    summary = summarize(report)
    queue = build_review_queue(report)
    repeatability = compare_repeatability(report)
    prefix = path.with_suffix("")
    scored_path = prefix.with_name(prefix.name + "-scored.json")
    review_path = prefix.with_name(prefix.name + "-review-queue.json")
    repeat_path = prefix.with_name(prefix.name + "-repeatability.json")
    markdown_path = prefix.with_name(prefix.name + "-human-review.md")
    scored_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps({"run_id": report["metadata"]["run_id"],
                                       "summary": summary, "queue": queue},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    repeat_path.write_text(json.dumps({"run_id": report["metadata"]["run_id"],
                                       "cases": repeatability},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# D3 人工审查包", "", f"Run ID: `{report['metadata']['run_id']}`", "",
             "以下规则只提供线索；请按 D1 四轴 rubric 独立给 0/1/2 分并记录证据与理由。",
             "来源列表不代表逐句 citation 验证。", "", "## 首轮逐题审查队列", ""]
    for item in queue:
        lines.extend([
            f"### {item['query_id']} — {', '.join(item['scenario'])}", "",
            f"**首轮答案：** {item['answer']}", "",
            f"**预期事实：** {'；'.join(item['expected_facts']) or '无；应拒答'}", "",
            f"**预期证据 ID：** {item['expected_evidence_ids']}", "",
            f"**拒答依据：** {item['refusal_reason'] or '不适用'}", "",
            f"**确定性分类：** `{item['classification']}`；证据线索见同名 review-queue JSON。", "",
            f"**待审原因：** {item['review_reason']}", "",
            f"**Rubric 问题：** {item['rubric_question']}", "",
            "**人工记录：** factual correctness __ / completeness __ / grounding __ / refusal correctness __；审查人 __；证据与理由 __。",
            "",
        ])
    lines.extend(["## 重复性观察", "", "每题在首轮之外追加两次。以下是描述性观察，不能据此作统计显著性或 SLO 结论。", ""])
    for case in repeatability:
        lines.extend([
            f"### {case['query_id']}", "",
            f"预选原因：{case['selection_reason']}", "",
            f"文本变化：{case['generation_text_varies']}；检索候选变化：{case['retrieval_candidate_ids_vary']}；上下文变化：{case['context_ids_vary']}；规则变化：{case['deterministic_rules_vary']}。",
            "人工评分分歧：待审。事实、grounding 与拒答语义变化须人工裁决。", "",
        ])
        for answer in case["answers"]:
            lines.extend([f"**第 {answer['attempt']} 次：** {answer['answer']}", ""])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {"summary": summary, "scored_baseline": str(scored_path),
            "review_queue": str(review_path),
            "repeatability": str(repeat_path), "human_review": str(markdown_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    args = parser.parse_args()
    print(json.dumps(make_package(args.baseline), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
