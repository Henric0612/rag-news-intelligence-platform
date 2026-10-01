"""D4 contracts exercise production RAG/search/SSE with deterministic AI doubles."""
import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import faiss
import numpy as np
import pytest
from langchain_core.language_models.fake import FakeListLLM

from Backend.models import db, User, KnowledgeItem
from Backend.services import rag_service as rag_module
from Backend.services.llm_service import LLMService
from Backend.services.rag_service import RAGService
from Backend.services.search_service import SearchService
from Backend.services.vector_service import VectorService
from Backend.services.rag_observability import (
    RequestTrace, RAGMetrics, active_trace, get_metrics, latency_summary,
)
from Backend.utils.jwt_utils import create_access_token

pytestmark = pytest.mark.ci
QUERY = 'QUERY_CANARY_private_request'
CONTEXT = 'CONTEXT_CANARY_private_uploaded_content'
ANSWER = 'ANSWER_CANARY_private_generated_response。'
SECRET = 'SECRET_CANARY_private_option'


@pytest.fixture
def rag(app, monkeypatch):
    db.session.add(KnowledgeItem(id=8101, title='metadata title', content=CONTEXT,
                                 source_type='manual', status='published'))
    db.session.commit()
    vector = VectorService.__new__(VectorService)
    vector.dimension = 384
    vector.embedding_model = SimpleNamespace(embed_query=lambda text: np.ones(384))
    vector.faiss_index = faiss.IndexFlatIP(384)
    vector.faiss_index.add(np.ones((1, 384), dtype='float32'))
    vector.id_mapping = {0: 8101}
    search = SearchService.__new__(SearchService)
    search.vector_service = vector
    search.cache_enabled = False
    search.rerank_model = SimpleNamespace(model=SimpleNamespace(score=lambda pairs: [1.] * len(pairs)))
    llm = LLMService.__new__(LLMService)
    llm.model_name = 'qwen3:8b'
    llm.llm = FakeListLLM(responses=[ANSWER])
    service = RAGService.__new__(RAGService)
    service.vector_service = vector
    service.search_service = search
    service.llm_service = llm
    service.default_top_k = 20
    service.rerank_top_k = 5
    service.max_context_length = 4000
    service.enable_rerank = True
    service.enable_web_fallback = False
    service._initialize_rag_chain()
    monkeypatch.setattr('Backend.routes.rag.get_rag_service', lambda: service)
    return service


@pytest.fixture
def tokens(app):
    headers = {}
    for role in ('user', 'admin'):
        user = User(username='d4-'+role, email=role+'@d4.invalid', role=role,
                    password_hash='unused-in-contract')
        db.session.add(user)
        db.session.flush()
        headers[role] = {'Authorization': 'Bearer ' + create_access_token(user.id)}
    db.session.commit()
    return headers


def events(caplog):
    return [json.loads(record.getMessage()) for record in caplog.records
            if record.name.endswith('rag_observability')]


def final_event(caplog):
    return [event for event in events(caplog) if event['event'] == 'request_end'][-1]


def sse(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).splitlines()
            if line.startswith('data: ')]


def ask(client, tokens, **kwargs):
    return client.post('/api/rag/ask', headers=tokens['user'],
                       json={'query': QUERY, **kwargs})


def test_normal_real_boundaries_and_correlation(client, rag, tokens, caplog):
    request_id = str(uuid.uuid4())
    headers = {**tokens['user'], 'X-Request-ID': request_id}
    response = client.post('/api/rag/ask', headers=headers, json={'query': QUERY})
    assert response.status_code == 200
    assert response.json['data']['answer'] == ANSWER
    assert response.headers['X-Request-ID'] == request_id
    recorded = events(caplog)
    assert {event['request_id'] for event in recorded} == {request_id}
    assert recorded[0]['event'] == 'request_start'
    end = final_event(caplog)
    assert end['status'] == 'success'
    assert end['candidate_count'] == 1
    assert end['reranking_state'] == 'executed'
    for name in ('query_embedding', 'candidate_retrieval', 'record_loading',
                 'reranking', 'context_construction', 'generation', 'total'):
        assert end['timings_ms'][name] is not None
        assert end['timings_ms'][name] >= 0
    assert end['timings_ms']['streaming_ttft'] is None
    assert end['timings_ms']['streaming_completion'] is None
    assert get_metrics().snapshot()['requests']['active'] == 0


@pytest.mark.parametrize('state', ['disabled', 'unavailable', 'empty', 'failed'])
def test_reranking_execution_and_skip_states(rag, caplog, state):
    options = {'enable_rerank': state != 'disabled'}
    if state == 'unavailable':
        rag.search_service.rerank_model = None
    elif state == 'empty':
        rag.search_service.semantic_search = lambda *args: {'results': []}
        rag.llm_service.generate_answer = Mock(return_value={'answer': ANSWER})
    elif state == 'failed':
        rag.search_service.rerank_model.model.score = Mock(side_effect=ValueError(SECRET))
    rag.answer_question(QUERY, options=options)
    end = final_event(caplog)
    assert end['reranking_state'] == ('failed' if state == 'failed' else 'skipped_'+state)
    assert (end['timings_ms']['reranking'] is not None) == (state == 'failed')
    if state == 'failed':
        assert end['error_categories'] == ['reranking_failure']
    assert SECRET not in caplog.text


@pytest.mark.parametrize('reason', ['no_vectors', 'no_semantic_results', 'retrieval_error'])
def test_retrieval_fallback_is_visible_and_preserves_results(rag, caplog, reason):
    search = rag.search_service
    search._keyword_search = lambda *args: [{'id': 8101, 'title': 'title', 'content': CONTEXT}]
    if reason == 'no_vectors':
        search.vector_service.id_mapping = {}
    elif reason == 'no_semantic_results':
        search.vector_service.search_similar = lambda *args: (np.array([]), [])
    else:
        search.vector_service.vectorize_text = Mock(side_effect=ValueError(QUERY + SECRET))
    result = rag.answer_question(QUERY)
    assert result['answer'] == ANSWER
    end = final_event(caplog)
    assert 'keyword_'+reason in end['fallback_categories']
    assert end['status'] == 'success'
    if reason == 'no_vectors':
        assert end['timings_ms']['query_embedding'] is None
        assert end['timings_ms']['record_loading'] is None
    if reason == 'retrieval_error':
        assert 'retrieval_failure' in end['error_categories']
    assert end['timings_ms']['candidate_retrieval'] is not None
    assert QUERY not in caplog.text and SECRET not in caplog.text


def test_normal_generation_failure_and_exception_privacy(rag, caplog):
    rag.llm_service.llm = None
    rag.llm_service.generate_answer = Mock(return_value={'error': QUERY + CONTEXT + SECRET})
    result = rag.answer_question(QUERY)
    assert result['error_code'] == 'AI_DEPENDENCY_UNAVAILABLE'
    end = final_event(caplog)
    assert end['status'] == 'failure'
    assert end['error_categories'] == ['generation_failure']
    assert 'legacy_generation' in end['fallback_categories']
    assert end['timings_ms']['generation'] is not None
    for text in (QUERY, CONTEXT, SECRET):
        assert text not in caplog.text


def test_unexpected_application_exception_finishes_request(rag, caplog):
    rag.search_service.semantic_search = Mock(side_effect=ValueError(QUERY))
    result = rag.answer_question(QUERY)
    assert result['error_code'] == 'RAG_REQUEST_FAILED'
    end = final_event(caplog)
    assert end['error_categories'] == ['application_error']
    assert end['status'] == 'failure'
    assert end['timings_ms']['generation'] is None
    assert get_metrics().snapshot()['requests']['active'] == 0
    assert QUERY not in caplog.text


def test_successful_sse_protocol_ttft_and_generation(client, rag, tokens, caplog):
    response = ask(client, tokens, stream=True)
    body = sse(response)
    response.close()
    assert response.mimetype == 'text/plain'
    assert [event['type'] for event in body] == [
        'thinking', 'thinking', 'thinking', 'sources', 'content', 'done']
    assert body[-2] == {'type': 'content', 'data': ANSWER}
    end = final_event(caplog)
    assert end['request_id'] == response.headers['X-Request-ID']
    assert end['status'] == 'success'
    assert 0 <= end['timings_ms']['streaming_ttft'] <= end['timings_ms']['streaming_completion']
    assert end['timings_ms']['generation'] is not None
    assert end['timings_ms']['streaming_completion'] <= end['timings_ms']['total']
    assert get_metrics().snapshot()['requests']['streaming'] == 1
    assert get_metrics().snapshot()['requests']['success'] == 1
    assert active_trace() is None


@pytest.mark.parametrize('consume_content', [False, True])
def test_sse_disconnect_closes_model_generator_and_counts_interruption(client, rag, tokens, caplog, consume_content):
    closed = []
    def content(*args):
        try:
            yield ANSWER
            yield ANSWER
        finally:
            closed.append(True)
    rag.llm_service.stream_response = content
    response = ask(client, tokens, stream=True)
    if consume_content:
        for data in response.response:
            if '"type": "content"' in data.decode():
                break
    response.close()
    end = final_event(caplog)
    assert end['status'] == 'interrupted'
    assert end['error_categories'] == ['streaming_interruption']
    assert end['timings_ms']['streaming_completion'] is None
    assert (end['timings_ms']['streaming_ttft'] is not None) == consume_content
    if consume_content:
        assert closed == [True]
    counts = get_metrics().snapshot()['requests']
    assert counts['active'] == 0 and counts['success'] == 0 and counts['interrupted'] == 1
    assert active_trace() is None


def test_stream_failure_after_content_is_not_success(client, rag, tokens, caplog):
    def broken(*args):
        yield ANSWER
        raise ConnectionError(QUERY + CONTEXT + SECRET)
    rag.llm_service.stream_response = broken
    response = ask(client, tokens, stream=True)
    body = sse(response)
    response.close()
    assert body[-1]['code'] == 'AI_DEPENDENCY_UNAVAILABLE'
    assert not any(event['type'] == 'done' for event in body)
    end = final_event(caplog)
    assert end['status'] == 'failure'
    assert end['error_categories'] == ['generation_failure']
    assert end['timings_ms']['streaming_ttft'] is not None
    assert end['timings_ms']['streaming_completion'] is None
    assert get_metrics().snapshot()['requests']['active'] == 0
    for text in (QUERY, CONTEXT, SECRET, ANSWER):
        assert text not in caplog.text


def test_stream_no_results_is_failure_with_null_generation(rag, caplog):
    rag.search_service.semantic_search = lambda *args: {'results': []}
    body = list(rag.stream_answer(QUERY))
    assert body[-1]['type'] == 'error'
    end = final_event(caplog)
    assert end['error_categories'] == ['no_results']
    assert end['timings_ms']['generation'] is None
    assert end['timings_ms']['streaming_ttft'] is None
    assert end['status'] == 'failure'


def test_stream_context_does_not_leak_between_interleaved_generators(rag, caplog):
    first, second = rag.stream_answer(QUERY), rag.stream_answer(QUERY)
    next(first)
    assert active_trace() is None
    next(second)
    assert active_trace() is None
    first.close(); second.close()
    ends = [event for event in events(caplog) if event['event'] == 'request_end']
    assert len({event['request_id'] for event in ends}) == 2
    assert all(event['status'] == 'interrupted' for event in ends)
    assert get_metrics().snapshot()['requests']['active'] == 0


def test_metrics_access_and_payload_privacy(client, rag, tokens, caplog):
    caplog.set_level(logging.DEBUG)
    client.set_cookie('d4-cookie', 'COOKIE_CANARY_private_cookie')
    response = client.post('/api/rag/ask', headers={**tokens['user'], 'X-Request-ID': SECRET},
                           json={'query': QUERY, 'options': {'secret': SECRET}})
    assert response.status_code == 200
    assert response.headers['X-Request-ID'] != SECRET
    assert client.get('/api/rag/metrics').status_code == 401
    assert client.get('/api/rag/metrics', headers=tokens['user']).status_code == 403
    response = client.get('/api/rag/metrics', headers=tokens['admin'])
    assert response.status_code == 200 and response.is_json
    snapshot = response.json['data']
    assert set(snapshot) == {'schema_version', 'process', 'requests', 'reranking',
                             'fallbacks', 'errors', 'latency'}
    assert snapshot['process']['persistent'] is False
    assert snapshot['requests']['started'] == snapshot['requests']['completed'] == 1
    assert snapshot['reranking']['executed'] == 1
    assert snapshot['latency']['stages']['streaming_ttft']['count'] == 0
    assert snapshot['latency']['stages']['streaming_ttft']['p50_ms'] is None
    assert snapshot['latency']['stages']['generation']['count'] == 1
    data = json.dumps(snapshot) + caplog.text
    for sensitive in (QUERY, CONTEXT, ANSWER, SECRET, 'COOKIE_CANARY_private_cookie',
                      *[h['Authorization'] for h in tokens.values()],
                      *[h['Authorization'][:20] for h in tokens.values()]):
        assert sensitive not in data


def test_stream_route_startup_failure_has_id_and_no_active_state(client, tokens, monkeypatch, caplog):
    monkeypatch.setattr('Backend.routes.rag.get_rag_service', Mock(side_effect=RuntimeError(SECRET)))
    response = ask(client, tokens, stream=True)
    assert response.status_code == 500 and response.headers.get('X-Request-ID')
    assert final_event(caplog)['status'] == 'failure'
    assert get_metrics().snapshot()['requests']['active'] == 0
    assert SECRET not in caplog.text


def test_request_timing_uses_monotonic_clock_and_finish_is_idempotent(monkeypatch):
    ticks = iter([10., 11., 11.5, 12.])
    monkeypatch.setattr('Backend.services.rag_observability.time.perf_counter', lambda: next(ticks))
    metrics = RAGMetrics()
    trace = RequestTrace('normal', metrics=metrics)
    with trace.stage('query_embedding'):
        pass
    trace.finish(); trace.finish()
    snapshot = metrics.snapshot()
    assert trace.timings['query_embedding'] == 500.
    assert trace.timings['total'] == 2000.
    assert snapshot['requests']['completed'] == 1
    assert snapshot['requests']['active'] == 0


def test_metrics_window_math_and_restart_reset():
    metrics = RAGMetrics(sample_limit=3)
    for duration in [10., 20., 30., 40., 50.]:
        trace = RequestTrace('normal', metrics=metrics)
        trace.timings['generation'] = duration
        trace.finish()
    snapshot = metrics.snapshot()
    summary = snapshot['latency']['stages']['generation']
    assert summary['count'] == 3 and summary['observed_count'] == 5
    assert summary['p50_ms'] == 40. and summary['p95_ms'] == 50.
    assert snapshot['requests']['success'] == 5
    restarted = RAGMetrics().snapshot()
    assert restarted['process']['instance_id'] != snapshot['process']['instance_id']
    assert restarted['requests']['started'] == 0
    assert all(stage['count'] == 0 for stage in restarted['latency']['stages'].values())
    assert latency_summary([])['p95_ms'] is None
    assert latency_summary([5., 10.])['p50_ms'] == 5.


def test_retrieval_failure_after_keyword_fallback_has_category(rag, caplog):
    rag.search_service.vector_service.vectorize_text = Mock(side_effect=RuntimeError(SECRET))
    rag.search_service._keyword_search = Mock(side_effect=RuntimeError(CONTEXT))
    rag.llm_service.generate_answer = Mock(return_value={'answer': ANSWER})
    rag.answer_question(QUERY)
    end = final_event(caplog)
    assert 'retrieval_failure' in end['error_categories']
    assert end['candidate_count'] == 0
    assert 'keyword_retrieval_error' in end['fallback_categories']
    assert CONTEXT not in caplog.text and SECRET not in caplog.text


def test_direct_stream_llm_failure_before_first_content_has_null_ttft(rag, caplog):
    def broken(*args):
        raise ConnectionError(SECRET)
        yield
    rag.llm_service.stream_response = broken
    body = list(rag.stream_answer(QUERY))
    assert body[-1]['code'] == 'AI_DEPENDENCY_UNAVAILABLE'
    end = final_event(caplog)
    assert end['status'] == 'failure'
    assert end['timings_ms']['generation'] is not None
    assert end['timings_ms']['streaming_ttft'] is None
    assert get_metrics().snapshot()['requests']['failure'] == 1


def test_caught_provider_error_messages_never_reach_runtime_logs(rag, caplog, monkeypatch):
    # Both actual LLM request methods catch provider exceptions containing text.
    class BrokenLLM(FakeListLLM):
        def _call(self, *args, **kwargs):
            raise RuntimeError(QUERY + CONTEXT + ANSWER + SECRET)
    rag.llm_service.llm = BrokenLLM(responses=[])
    assert rag.answer_question(QUERY)['error_code'] == 'AI_DEPENDENCY_UNAVAILABLE'
    assert list(rag.stream_answer(QUERY))[-1]['code'] == 'AI_DEPENDENCY_UNAVAILABLE'
    assert get_metrics().snapshot()['requests']['failure'] == 2
    for text in (QUERY, CONTEXT, ANSWER, SECRET):
        assert text not in caplog.text


def test_baseline_cold_warm_separation_and_integrity():
    from Backend.evaluation.latency import summarize_observations, validate_observations
    def row(duration, kind, mode='normal'):
        from Backend.services.rag_observability import STAGES
        timings = dict.fromkeys(STAGES)
        timings.update(generation=duration, total=duration + 10)
        if mode == 'streaming':
            timings.update(streaming_ttft=1., streaming_completion=duration + 5)
        return {'request_id': str(uuid.uuid4()), 'status': 'success', 'runtime_mode': mode,
                'sample_kind': kind, 'timings_ms': timings}
    rows = [row(10000, 'cold'), row(2000, 'warmup'), row(10, 'warm'), row(20, 'warm'), row(30, 'warm', 'streaming')]
    summary = summarize_observations(rows)
    assert summary['normal']['sample_count'] == 2
    assert summary['normal']['stages']['generation']['p95_ms'] == 20
    assert summary['streaming']['sample_count'] == 1
    with pytest.raises(ValueError, match='duplicate'):
        validate_observations([rows[0], rows[0]])
    rows[-1]['timings_ms']['streaming_ttft'] = 100.
    with pytest.raises(ValueError, match='inconsistent'):
        validate_observations(rows)
    rows[-1]['timings_ms']['streaming_ttft'] = float('nan')
    with pytest.raises(ValueError, match='invalid'):
        validate_observations(rows)


def test_interruption_closes_retained_provider_iterator(rag, caplog):
    closed = []
    def chunks():
        try:
            yield ANSWER
            yield ANSWER
        finally:
            closed.append(True)
    provider = chunks()  # This reference prevents refcount cleanup from hiding leaks.
    rag.llm_service.llm = Mock(stream=Mock(return_value=provider))
    outer = rag.stream_answer(QUERY)
    for event in outer:
        if event['type'] == 'content':
            break
    outer.close()
    assert closed == [True]
    assert final_event(caplog)['status'] == 'interrupted'
    assert get_metrics().snapshot()['requests']['active'] == 0


def test_failure_inside_generation_stage_is_classified_in_stage_event(rag, caplog):
    rag.llm_service.llm = None
    rag.llm_service.generate_answer = Mock(return_value={'error': SECRET})
    rag.answer_question(QUERY)
    end = [event for event in events(caplog) if event['event'] == 'stage_end' and event['stage'] == 'generation'][-1]
    assert end['status'] == 'failed'
    assert end['error_categories'] == ['generation_failure']


def test_swallowed_database_errors_mark_both_attempted_stages_failed(rag, caplog, monkeypatch):
    monkeypatch.setattr(db.session, 'query', Mock(side_effect=RuntimeError(SECRET)))
    rag.answer_question(QUERY)
    stages = [event for event in events(caplog) if event['event'] == 'stage_end']
    assert [e for e in stages if e['stage'] == 'record_loading'][0]['status'] == 'failed'
    assert [e for e in stages if e['stage'] == 'candidate_retrieval'][-1]['status'] == 'failed'
    assert 'retrieval_failure' in final_event(caplog)['error_categories']
    assert SECRET not in caplog.text


@pytest.mark.parametrize('streaming', [False, True])
def test_web_fallback_is_timed_without_changing_response(rag, caplog, streaming):
    rag.search_service.semantic_search = lambda *args: {'results': []}
    rag.search_service.web_fallback_search = Mock(return_value={
        'results': [{'id': 'web_1', 'title': 'title', 'content': CONTEXT}]})
    if streaming:
        body = list(rag.stream_answer(QUERY, options={'enable_web_fallback': True}))
        assert body[-1]['type'] == 'done'
        assert [event for event in body if event['type'] == 'sources'][0]['data']['web_search_used'] is True
    else:
        response = rag.answer_question(QUERY, options={'enable_web_fallback': True})
        assert response['web_search_used'] is True and response['answer'] == ANSWER
    end = final_event(caplog)
    assert end['fallback_categories'] == ['web_search']
    assert end['candidate_count'] == 1
    assert end['timings_ms']['candidate_retrieval'] is not None
    assert end['timings_ms']['query_embedding'] is None
    assert QUERY not in caplog.text and CONTEXT not in caplog.text
