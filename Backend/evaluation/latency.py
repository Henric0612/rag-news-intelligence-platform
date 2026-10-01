"""Finite D4 local latency observations; no quality tuning or load benchmark.

Run: .venv/bin/python -m Backend.evaluation.latency --output /tmp/rag-d4-native.json
The fixed D1 corpus, database, FAISS index and synthetic users are isolated.
Reports contain metadata/timings, never queries, contexts, prompts or answers.
"""
import argparse
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import time
import uuid

from .dataset import load_dataset
from .loader import isolated_evaluation
from .answer_run import runtime_metadata, run_one
from .retrieval import evaluate_questions
from Backend.services.rag_observability import STAGES, latency_summary


class EventCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        if record.name == 'Backend.services.rag_observability':
            self.events.append(json.loads(record.getMessage()))


def validate_observations(rows):
    ids = set()
    for row in rows:
        if row['request_id'] in ids:
            raise ValueError('duplicate baseline request ID')
        ids.add(row['request_id'])
        if row['status'] != 'success':
            raise ValueError('latency sample did not complete successfully')
        timings = row['timings_ms']
        if set(timings) != set(STAGES):
            raise ValueError('incomplete stage timing schema')
        for value in timings.values():
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not math.isfinite(value) or value < 0):
                raise ValueError('invalid stage latency')
        if timings['total'] is None or timings['generation'] is None:
            raise ValueError('missing required latency')
        if row['runtime_mode'] == 'streaming':
            if timings['streaming_ttft'] is None or timings['streaming_completion'] is None:
                raise ValueError('missing streaming latency')
            if not 0 <= timings['streaming_ttft'] <= timings['streaming_completion'] <= timings['total']:
                raise ValueError('inconsistent streaming latency order')
        elif timings['streaming_ttft'] is not None or timings['streaming_completion'] is not None:
            raise ValueError('normal request has streaming latency')


def summarize_observations(rows):
    validate_observations(rows)
    warm = [row for row in rows if row['sample_kind'] == 'warm']
    return {
        mode: {
            'sample_count': sum(row['runtime_mode'] == mode for row in warm),
            'stages': {stage: latency_summary([
                row['timings_ms'][stage] for row in warm
                if row['runtime_mode'] == mode and row['timings_ms'][stage] is not None
            ]) for stage in STAGES},
        } for mode in ('normal', 'streaming')
    }


def run_real(output, repetitions=2):
    output = Path(output).resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents or output.exists():
        raise ValueError('choose a new output path outside the repository')
    if not 1 <= repetitions <= 5:
        raise ValueError('finite local observations require 1 to 5 repetitions')
    dataset = load_dataset()
    questions = {q['id']: q for q in dataset['questions']}
    run_id = 'd4-'+str(uuid.uuid4())
    report = {'metadata': {'run_id': run_id}, 'observations': []}
    # Kept only in memory to inspect the metadata-only captured events.
    sensitive_texts = [q['query'] for q in dataset['questions']]
    sensitive_texts += [r['content'] for r in dataset['records']]
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    from Backend.config import Config
    from Backend.models import db, User
    from Backend.utils.jwt_utils import create_access_token
    from Backend.services import vector_service as vm, search_service as sm
    from Backend.services import llm_service as lm, rag_service as rm
    from Backend.services.rag_observability import get_metrics
    import requests

    capture = EventCapture()
    event_logger = logging.getLogger('Backend.services.rag_observability')
    event_logger.addHandler(capture)
    try:
        with isolated_evaluation(dataset) as (app, paths):
            app.config['DATA_DIR'] = str(paths['root'])
            keys = ('EMBEDDING_MODEL', 'RERANK_MODEL', 'MODEL_CACHE_DIR', 'LLM_MODEL',
                    'OLLAMA_HOST', 'LLM_MAX_TOKENS', 'LLM_TEMPERATURE', 'RAG_DEFAULT_TOP_K',
                    'RAG_RERANK_TOP_K', 'RAG_MAX_CONTEXT_LENGTH', 'RAG_ENABLE_RERANK',
                    'RAG_ENABLE_WEB_FALLBACK', 'SEARCH_CACHE_ENABLED', 'SEARCH_CACHE_TTL',
                    'JWT_SECRET_KEY', 'JWT_ALGORITHM', 'JWT_ACCESS_TOKEN_EXPIRES')
            for key in keys:
                app.config[key] = getattr(Config, key)
            # Safe impact check: only this temporary evaluation DB is initialized.
            assert str(paths['database']) == db.engine.url.database
            db.create_all()
            users = {}
            for role in ('admin', 'user'):
                user = User(username='d4-'+role, email=role+'@d4.invalid', role=role,
                            password_hash='synthetic-validation-only')
                db.session.add(user); db.session.flush()
                users[role] = {'Authorization': 'Bearer '+create_access_token(user.id)}
            db.session.commit()
            from Backend.routes.rag import rag_bp
            from Backend.routes.health import health_bp
            app.register_blueprint(rag_bp)
            app.register_blueprint(health_bp)
            prior = (vm.vector_service, sm.search_service, lm.llm_service, rm.rag_service)
            started = time.perf_counter()
            vector = vm.VectorService()
            if vector.embedding_model.__class__.__name__ == 'RandomEmbeddings':
                raise RuntimeError('real embedding required')
            if not vector.build_faiss_index(vector.batch_vectorize([r['content'] for r in dataset['records']]),
                                            [r['id'] for r in dataset['records']]):
                raise RuntimeError('real FAISS indexing failed')
            setup_ms = (time.perf_counter() - started) * 1000
            vm.vector_service, sm.search_service, lm.llm_service, rm.rag_service = vector, None, None, None
            try:
                client = app.test_client()
                resident = requests.get(Config.OLLAMA_HOST+'/api/ps', timeout=5)
                resident.raise_for_status()
                report['metadata'].update({
                    'vector_setup_ms': setup_ms,
                    'cold_scope': 'first request of fresh RAG/search/LLM service; corpus embeddings already indexed',
                    'ollama_resident_before_first_request': [m.get('name') for m in resident.json().get('models', [])],
                    'baseline_note': 'informational local baseline only; not an SLO or load benchmark',
                    'selection': ['Q001', 'Q025'], 'warm_repetitions_per_question_per_mode': repetitions,
                })
                def sample(qid, mode, kind):
                    request_id = str(uuid.uuid4())
                    response = client.post('/api/rag/ask', headers={**users['user'], 'X-Request-ID': request_id},
                                           json={'query': questions[qid]['query'], 'stream': mode == 'streaming'})
                    try:
                        if mode == 'normal':
                            assert response.status_code == 200 and response.json['success']
                            sensitive_texts.append(response.json['data']['answer'])
                        else:
                            data = [json.loads(line[6:]) for line in response.get_data(as_text=True).splitlines()
                                    if line.startswith('data: ')]
                            assert data[-1]['type'] == 'done' and not any(x['type'] == 'error' for x in data)
                            sensitive_texts.append(''.join(x['data'] for x in data if x['type'] == 'content'))
                        assert response.headers['X-Request-ID'] == request_id
                    finally:
                        response.close()
                    end = [e for e in capture.events if e['request_id'] == request_id and e['event'] == 'request_end']
                    if len(end) != 1:
                        raise ValueError('request finalization/correlation failed')
                    if end[0]['error_categories'] or end[0]['reranking_state'] != 'executed':
                        raise ValueError('real latency baseline requires successful reranking without errors')
                    report['observations'].append({**end[0], 'question_id': qid, 'sample_kind': kind})
                    save()
                    print(f'{qid} {mode} {kind} saved', flush=True)
                sample('Q001', 'normal', 'cold')
                rag = rm.get_rag_service()
                if rag.search_service.rerank_model is None:
                    raise RuntimeError('real CrossEncoder required')
                report['metadata'].update(runtime_metadata(rag, dataset, run_id))
                report['metadata'].update({'runtime_mode': 'WSL native; production Flask RAG routes; isolated D1 SQLite/FAISS',
                                          'embedding_model': app.config['EMBEDDING_MODEL'],
                                          'reranker_model': app.config['RERANK_MODEL']})
                sample('Q001', 'streaming', 'warmup')
                for mode in ('normal', 'streaming'):
                    for qid in ('Q001', 'Q025'):
                        for _ in range(repetitions):
                            sample(qid, mode, 'warm')
                # Check runnable D2/D3 paths without rewriting their accepted baselines.
                d2 = evaluate_questions(dataset, rag.search_service)
                report['regression_probes'] = {'d2_question_count': len(d2['queries'])}
                d3 = run_one(rag, questions['Q001'], run_id=run_id, attempt=1)
                report['regression_probes']['d3_question_id'] = d3['question_id'] if 'question_id' in d3 else 'Q001'
                report['regression_probes']['d3_path_completed'] = True
                # Safe probes affect only this temporary application's in-memory
                # state, and are excluded from warm/cold latency distributions.
                report['runtime_probes'] = []
                def probe(payload, *, disconnect=False):
                    rid = str(uuid.uuid4())
                    response = client.post('/api/rag/ask', headers={**users['user'], 'X-Request-ID': rid},
                                           json=payload)
                    try:
                        if disconnect:
                            for data in response.response:
                                if '"type": "content"' in data.decode():
                                    break
                        else:
                            assert response.status_code == 200 and response.json['success']
                    finally:
                        response.close()
                    end = [e for e in capture.events if e['request_id'] == rid and e['event'] == 'request_end']
                    assert len(end) == 1
                    report['runtime_probes'].append(end[0])
                    return end[0]
                assert probe({'query': questions['Q001']['query'], 'enable_rerank': False})['reranking_state'] == 'skipped_disabled'
                mapping = vector.id_mapping
                try:
                    vector.id_mapping = {}
                    fallback = probe({'query': '东站'})
                    assert 'keyword_no_vectors' in fallback['fallback_categories']
                    assert fallback['timings_ms']['query_embedding'] is None
                finally:
                    vector.id_mapping = mapping
                interrupted = probe({'query': questions['Q001']['query'], 'stream': True}, disconnect=True)
                assert interrupted['status'] == 'interrupted'
                assert interrupted['error_categories'] == ['streaming_interruption']
                access = [client.get('/api/rag/metrics').status_code,
                          client.get('/api/rag/metrics', headers=users['user']).status_code,
                          client.get('/api/rag/metrics', headers=users['admin']).status_code]
                assert access == [401, 403, 200]
                report['access_statuses'] = access
                assert client.get('/api/health').status_code == 200
                assert client.get('/api/ready').status_code == 200
                report['health_readiness_statuses'] = [200, 200]
                report['metrics'] = get_metrics().snapshot()
                assert report['metrics']['requests']['active'] == 0
                report['summary'] = summarize_observations(report['observations'])
                ps = requests.get(Config.OLLAMA_HOST+'/api/ps', timeout=5).json()
                report['metadata']['ollama_gpu_residency_after'] = [
                    {k: m.get(k) for k in ('name', 'size', 'size_vram')} for m in ps.get('models', [])]
                assert any(m['name'] == Config.LLM_MODEL and m['size_vram'] > 0
                           for m in report['metadata']['ollama_gpu_residency_after'])
                report['metadata']['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
                captured = json.dumps(capture.events, ensure_ascii=False)
                for value in sensitive_texts + [headers['Authorization'] for headers in users.values()]:
                    if value and value in captured:
                        raise ValueError('sensitive text found in structured runtime events')
                report['privacy_inspection'] = 'no full-text payload or authorization value in structured events'
                save()
            finally:
                vm.vector_service, sm.search_service, lm.llm_service, rm.rag_service = prior
    finally:
        event_logger.removeHandler(capture)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--repetitions', type=int, default=2)
    args = parser.parse_args()
    run_real(args.output, args.repetitions)


if __name__ == '__main__':
    main()
