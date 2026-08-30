"""Health/readiness API tests."""
from unittest.mock import Mock, patch


class TestSprint1HealthAPI:
    def test_health_check(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['data']['status'] == 'healthy'
        assert 'timestamp' in result['data']
        assert 'version' in result['data'] or 'uptime' in result['data']

    def test_readiness_check(self, client):
        response = client.get('/api/ready')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['data']['status'] == 'ready'
        assert result['data']['database'] in ['connected', 'ready', True]

    def test_health_check_includes_system_info(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()['data']
        assert 'status' in data
        assert 'timestamp' in data

    def test_health_endpoints_no_auth_required(self, client):
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/ready').status_code == 200

    def test_quick_readiness_does_not_initialize_ai(self, client):
        with patch('Backend.services.vector_service.get_vector_service') as vector_mock, \
             patch('Backend.services.search_service.get_search_service') as search_mock:
            response = client.get('/api/ready?quick=true')

        assert response.status_code == 200
        vector_mock.assert_not_called()
        search_mock.assert_not_called()
        assert response.get_json()['data']['quick_mode'] is True

    def test_full_readiness_requires_ai_dependencies(self, client):
        vector_service = Mock(embedding_model=Mock())
        search_service = Mock(rerank_model=Mock())
        tags_response = Mock()
        tags_response.raise_for_status.return_value = None
        tags_response.json.return_value = {'models': [{'name': 'qwen3:8b'}]}

        with patch('Backend.services.vector_service.get_vector_service', return_value=vector_service), \
             patch('Backend.services.search_service.get_search_service', return_value=search_service), \
             patch('Backend.routes.health.requests.get', return_value=tags_response):
            response = client.get('/api/ready?quick=false')

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['embedding'] == 'ready'
        assert data['reranker'] == 'ready'
        assert data['ollama'] == 'ready'
        assert data['llm_model'] == 'ready'

    def test_full_readiness_returns_503_when_ollama_is_unavailable(self, client):
        vector_service = Mock(embedding_model=Mock())
        search_service = Mock(rerank_model=Mock())
        with patch('Backend.services.vector_service.get_vector_service', return_value=vector_service), \
             patch('Backend.services.search_service.get_search_service', return_value=search_service), \
             patch('Backend.routes.health.requests.get', side_effect=ConnectionError('offline')):
            ready_response = client.get('/api/ready?quick=false')

        assert ready_response.status_code == 503
        assert client.get('/api/health').status_code == 200
