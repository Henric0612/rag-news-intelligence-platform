"""Focused Stage 8 regression tests for RAG dependency failures."""

from unittest.mock import Mock, patch

from Backend.services.llm_service import LLMService
from Backend.services.rag_service import RAGService


def _rag_service_with_result(result):
    service = RAGService.__new__(RAGService)
    service.default_top_k = 5
    service.rerank_top_k = 5
    service.max_context_length = 4000
    service.enable_rerank = False
    service.enable_web_fallback = False
    service.search_service = Mock()
    service.search_service.semantic_search.return_value = {
        'results': [{'title': 'marker', 'content': 'unique validation fact'}],
        'response_time': 0.01,
    }
    service.llm_service = Mock()
    service.llm_service.llm = None
    service.llm_service.model_name = 'qwen3:8b'
    service.llm_service.generate_answer.return_value = result
    return service


def test_non_stream_ai_failure_returns_503_contract(client, auth_headers):
    rag_service = Mock()
    rag_service.answer_question.return_value = {
        'error': True,
        'error_code': 'AI_DEPENDENCY_UNAVAILABLE',
    }

    with patch('Backend.routes.rag.get_rag_service', return_value=rag_service):
        response = client.post(
            '/api/rag/ask',
            json={'query': 'dependency contract', 'stream': False},
            headers=auth_headers,
        )

    body = response.get_json()
    assert response.status_code == 503
    assert body['success'] is False
    assert body['data']['error_code'] == 'AI_DEPENDENCY_UNAVAILABLE'


def test_non_stream_success_contract_remains_compatible(client, auth_headers):
    rag_service = Mock()
    rag_service.answer_question.return_value = {
        'answer': 'normal answer',
        'sources': [],
    }

    with patch('Backend.routes.rag.get_rag_service', return_value=rag_service):
        response = client.post(
            '/api/rag/ask',
            json={'query': 'success contract', 'stream': False},
            headers=auth_headers,
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body['success'] is True
    assert body['data']['answer'] == 'normal answer'


def test_service_preserves_ai_dependency_failure():
    service = _rag_service_with_result({'error': 'Ollama connection refused'})

    result = service.answer_question(
        'dependency contract', options={'enable_rerank': False}
    )

    assert result['error'] is True
    assert result['error_code'] == 'AI_DEPENDENCY_UNAVAILABLE'


def test_stream_ai_failure_emits_error_without_done_event():
    service = _rag_service_with_result({})

    def unavailable_stream(*args, **kwargs):
        raise ConnectionError('Ollama connection refused')
        yield  # pragma: no cover - keeps this function a generator

    service.llm_service.stream_response.side_effect = unavailable_stream

    events = list(
        service.stream_answer(
            'dependency contract', options={'enable_rerank': False}
        )
    )

    assert events[-1] == {
        'type': 'error',
        'code': 'AI_DEPENDENCY_UNAVAILABLE',
        'message': 'AI服务暂时不可用，请稍后重试。',
    }
    assert not any(event.get('type') == 'done' for event in events)


def test_llm_request_reinitializes_after_dependency_recovers():
    service = LLMService.__new__(LLMService)
    service.llm = None
    service.model_name = 'qwen3:8b'
    service.build_prompt = Mock(return_value='prompt')
    service.evaluate_answer_quality = Mock(return_value=1.0)
    service.format_response = Mock(return_value={'answer': 'recovered'})
    recovered_llm = Mock()
    recovered_llm.invoke.return_value = 'recovered'

    def recover_client():
        service.llm = recovered_llm

    service._initialize_client = Mock(side_effect=recover_client)

    result = service.generate_answer('query', [])

    service._initialize_client.assert_called_once_with()
    assert result['answer'] == 'recovered'
    assert 'error' not in result
