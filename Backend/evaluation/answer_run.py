"""Run D3 through the unmodified production RAG answer method on D1 storage."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import uuid

from .answer import score_result, summarize, validate_report
from .dataset import DATASET_PATH, load_dataset
from .loader import isolated_evaluation


# Fixed before observing any answer. Reasons refer only to D1 labels.
PRESELECTED = {
    "Q001": "single_document / ordinary visible evidence",
    "Q002": "ambiguous_candidates / confusing_facts",
    "Q007": "truncation_sensitive / evidence beyond first 500 characters",
    "Q025": "multi_document synthesis",
    "Q028": "no_answer / refusal and grounding",
    "Q030": "truncation_sensitive / zero-valued fact and grounding",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class SearchTrace:
    """Observe production search calls without changing returned values."""

    def __init__(self, service):
        self.service = service
        self.candidates = []
        self.reranked = []
        self.search_type = None

    def semantic_search(self, *args, **kwargs):
        result = self.service.semantic_search(*args, **kwargs)
        self.candidates = [dict(item) for item in result.get("results", [])]
        self.search_type = result.get("search_type")
        return result

    def rerank_results(self, *args, **kwargs):
        result = self.service.rerank_results(*args, **kwargs)
        self.reranked = [dict(item) for item in result]
        return result

    def __getattr__(self, name):
        return getattr(self.service, name)


def run_one(rag, question, *, run_id, attempt):
    trace = SearchTrace(rag.search_service)
    rag.search_service = trace
    try:
        response = rag.answer_question(question["query"])
    finally:
        rag.search_service = trace.service
    if response.get("error") or response.get("error_code"):
        raise RuntimeError(f'{question["id"]} attempt {attempt}: RAG error {response.get("error_code", response.get("error"))}')
    candidate_ids = [item["id"] for item in trace.candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("duplicate retrieved candidate IDs")
    source_ids = [item["id"] for item in response.get("sources", [])]
    if trace.reranked and source_ids != [item["id"] for item in trace.reranked[:rag.rerank_top_k]]:
        raise ValueError("production source identity differs from reranking trace")
    # build_context is the actual production method and receives the same source
    # dictionaries as the answer path. It is deterministic and has no side effect.
    context = rag.build_context(response.get("sources", []))
    row = score_result(question, response.get("answer"), candidate_ids, context,
                       run_id=run_id, attempt=attempt, timestamp=utc_now())
    row["search_type"] = trace.search_type
    row["retrieval_trace"] = [{"id": item["id"], "rank": item.get("rank"),
                                "similarity_score": item.get("similarity_score"),
                                "keyword_score": item.get("keyword_score")}
                               for item in trace.candidates]
    row["reranking_trace"] = [{"id": item["id"], "rank": item.get("rank"),
                                "rerank_score": item.get("rerank_score")}
                               for item in trace.reranked]
    row["model"] = response.get("model")
    row["response_time_seconds"] = response.get("response_time")
    return row


def runtime_metadata(rag, dataset, run_id):
    import requests
    model = rag.llm_service.model_name
    host = rag.llm_service.ollama_host
    response = requests.get(f"{host}/api/tags", timeout=5)
    response.raise_for_status()
    available = {item["name"]: item for item in response.json()["models"]}
    if model not in available:
        raise RuntimeError(f"configured Ollama model {model} is unavailable")
    try:
        gpu = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        gpu = None
    llm = rag.llm_service.llm
    return {
        "run_id": run_id, "started_at_utc": utc_now(),
        "dataset_version": dataset["version"],
        "dataset_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
        "model_name": model, "exact_model_tag": available[model]["name"],
        "model_digest": available[model].get("digest"),
        "generation_explicit": {"temperature": llm.temperature,
                                "num_predict": llm.num_predict,
                                "top_p": llm.top_p, "top_k": llm.top_k},
        "other_ollama_parameters": "unspecified; Ollama / LangChain defaults",
        "runtime_mode": "WSL native; D1 isolated temporary SQLite/FAISS; production RAGService.answer_question",
        "platform": platform.platform(), "gpu_detected": gpu,
        "rag_config": {"candidate_k": rag.default_top_k, "rerank_k": rag.rerank_top_k,
                       "max_context_length": rag.max_context_length,
                       "enable_rerank": rag.enable_rerank,
                       "enable_web_fallback": rag.enable_web_fallback},
        "model_preprocessing": "production embedding/CrossEncoder and first-500-character search content",
    }


def run_real(output):
    output = Path(output).resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise ValueError("baseline output must be outside the repository")
    if output.exists():
        raise FileExistsError("baseline already exists; first-run answers cannot be replaced")
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset()
    if len(dataset["questions"]) != 30 or not set(PRESELECTED) <= {q["id"] for q in dataset["questions"]}:
        raise ValueError("D3 protocol requires the approved 30-question dataset")
    run_id = f"d3-{uuid.uuid4()}"
    report = {"metadata": {"run_id": run_id, "started_at_utc": utc_now(),
                            "protocol": "first 30 questions once, then two additional runs per selected question"},
              "repeatability_selection": PRESELECTED,
              "authoritative": [], "repeatability": []}
    write_json(output, report)  # Preserve selection and each first answer before inspection.
    from Backend.config import Config
    from Backend.services import vector_service as vector_module
    from Backend.services import search_service as search_module
    from Backend.services import llm_service as llm_module
    from Backend.services import rag_service as rag_module

    with isolated_evaluation(dataset) as (app, paths):
        app.config["DATA_DIR"] = str(paths["root"])
        for key in ("EMBEDDING_MODEL", "RERANK_MODEL", "MODEL_CACHE_DIR", "LLM_MODEL",
                    "OLLAMA_HOST", "LLM_MAX_TOKENS", "LLM_TEMPERATURE", "RAG_DEFAULT_TOP_K",
                    "RAG_RERANK_TOP_K", "RAG_MAX_CONTEXT_LENGTH", "RAG_ENABLE_RERANK",
                    "RAG_ENABLE_WEB_FALLBACK", "SEARCH_CACHE_ENABLED", "SEARCH_CACHE_TTL"):
            if hasattr(Config, key):
                app.config[key] = getattr(Config, key)
        vector = vector_module.VectorService()
        if vector.embedding_model is None:
            raise RuntimeError("real embedding model unavailable")
        if not vector.build_faiss_index(vector.batch_vectorize(
                [r["content"] for r in dataset["records"]]),
                [r["id"] for r in dataset["records"]]):
            raise RuntimeError("real FAISS index build failed")
        previous = (vector_module.vector_service, search_module.search_service,
                    llm_module.llm_service, rag_module.rag_service)
        vector_module.vector_service = vector
        search_module.search_service = None
        llm_module.llm_service = None
        rag_module.rag_service = None
        try:
            rag = rag_module.RAGService()
            if rag.search_service.rerank_model is None or rag.llm_service.llm is None:
                raise RuntimeError("real reranker or Ollama client unavailable")
            report["metadata"] = runtime_metadata(rag, dataset, run_id)
            write_json(output, report)
            for question in dataset["questions"]:
                report["authoritative"].append(run_one(rag, question, run_id=run_id, attempt=1))
                write_json(output, report)
                print(f'{question["id"]} first run saved', flush=True)
            for question in dataset["questions"]:
                if question["id"] in PRESELECTED:
                    for attempt in (2, 3):
                        report["repeatability"].append(run_one(
                            rag, question, run_id=run_id, attempt=attempt))
                        write_json(output, report)
                        print(f'{question["id"]} repeat {attempt} saved', flush=True)
        finally:
            (vector_module.vector_service, search_module.search_service,
             llm_module.llm_service, rag_module.rag_service) = previous
    validate_report(report, dataset)
    report["summary"] = summarize(report)
    report["metadata"]["finished_at_utc"] = utc_now()
    write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run_real(args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
