"""
测试配置和夹具
"""
import os
import sys
from pathlib import Path

import pytest
import tempfile
from unittest.mock import patch, Mock

# 确保Backend目录的父目录在Python路径中，以便作为包导入
backend_parent = Path(__file__).parent.parent.parent
if str(backend_parent) not in sys.path:
    sys.path.insert(0, str(backend_parent))


def pytest_configure(config):
    """Set paths before collection imports application/service configuration."""
    temporary = tempfile.TemporaryDirectory(prefix="rag-tests-")
    environment = pytest.MonkeyPatch()
    config.add_cleanup(temporary.cleanup)
    config.add_cleanup(environment.undo)
    root = Path(temporary.name)
    for key, value in {
        'RAG_DATA_DIR': root / 'data',
        'FAISS_INDEX_PATH': root / 'data/faiss/knowledge.index',
        'FAISS_ID_MAPPING_PATH': root / 'data/faiss/id_mapping.json',
        'DATABASE_URL': 'sqlite:///:memory:',
        'HF_HUB_OFFLINE': '1',
        'TRANSFORMERS_OFFLINE': '1',
        'HF_DATASETS_OFFLINE': '1',
    }.items():
        environment.setenv(key, str(value))


@pytest.fixture(autouse=True)
def ci_isolation(request, monkeypatch, tmp_path):
    """Guard only the approved CI tests; preserve real-model local test entrypoints."""
    if request.node.get_closest_marker('ci') is None:
        yield
        return

    import socket
    import smtplib
    import requests

    unexpected = []

    def blocked(*args, **kwargs):
        import traceback
        unexpected.append(''.join(traceback.format_stack(limit=8)))
        raise RuntimeError('CI tests must mock external dependencies')

    # Record attempts as well as raising: application handlers may catch exceptions.
    for owner, name in [
        (socket.socket, 'connect'), (socket.socket, 'connect_ex'),
        (socket.socket, 'sendto'), (socket, 'getaddrinfo'),
        (requests.sessions.Session, 'request'),
        (smtplib.SMTP, 'connect'),
    ]:
        monkeypatch.setattr(owner, name, blocked)

    from sentence_transformers import SentenceTransformer, CrossEncoder
    from Backend.services import vector_service, search_service, llm_service, rag_service
    from Backend.services.token_blacklist_service import TokenBlacklistService
    from Backend.config import TestingConfig

    for owner, name in [
        (SentenceTransformer, '__init__'), (CrossEncoder, '__init__'),
        (vector_service, 'HuggingFaceEmbeddings'),
        (search_service, 'HuggingFaceCrossEncoder'),
        (llm_service.LLMService, '_initialize_client'),
    ]:
        monkeypatch.setattr(owner, name, blocked)
    for module in (vector_service, search_service, llm_service, rag_service):
        monkeypatch.setattr(module, module.__name__.rsplit('.', 1)[-1], None)
    monkeypatch.setattr(TokenBlacklistService, '_blacklist', {})
    from Backend.services import data_service
    from Backend.services.file_service import FileService

    # crawler.py eagerly constructs DataService while registering unrelated routes.
    # Only this startup dependency is a stub; real model entrypoints stay guarded.
    vector_stub = Mock(spec_set=vector_service.VectorService)
    for name in dir(vector_service.VectorService):
        if not name.startswith('_') and callable(getattr(vector_service.VectorService, name)):
            getattr(vector_stub, name).side_effect = blocked
    monkeypatch.setattr(data_service, 'VectorService', Mock(return_value=vector_stub))

    def isolated_upload_dir(service):
        service.upload_dir = str(tmp_path / 'uploads')
        Path(service.upload_dir).mkdir(exist_ok=True)

    monkeypatch.setattr(FileService, '_ensure_upload_dir', isolated_upload_dir)
    monkeypatch.setattr(vector_service.VectorService, '_resolve_data_dir',
                        lambda self: str(tmp_path / 'data'))

    monkeypatch.setattr(TestingConfig, 'MODEL_CACHE_DIR', str(tmp_path / 'models'))
    for key in ('HF_HOME', 'HF_HUB_CACHE', 'MODEL_CACHE_DIR', 'TORCH_HOME'):
        monkeypatch.setenv(key, str(tmp_path / 'models'))

    # Routes cache service instances at import time. Rebind their test-owned state
    # on every CI test so no object keeps an earlier test's path or guard callback.
    from Backend.routes.crawler import data_service as crawler_data
    from Backend.routes.upload import file_service as upload_files
    monkeypatch.setattr(crawler_data, 'vector_service', vector_stub)
    for service in (crawler_data.file_service, upload_files):
        monkeypatch.setattr(service, 'upload_dir', str(tmp_path / 'uploads'))
    try:
        yield
    finally:
        assert not unexpected, "CI external dependency guard:\n" + "\n".join(unexpected)


@pytest.fixture
def app(ci_isolation, monkeypatch):
    """TestingConfig binds a fresh in-memory SQLite engine before app initialization."""
    from Backend.app import create_app
    from Backend.config import TestingConfig
    from Backend.models import db

    monkeypatch.setattr(TestingConfig, 'JWT_SECRET_KEY', 'c1-test-secret-key-for-local-contracts')
    assert TestingConfig.TESTING is True
    assert TestingConfig.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'
    application = create_app('testing')

    def assert_test_database():
        assert application.testing is True
        assert application.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
        assert db.engine.url.get_backend_name() == 'sqlite'
        assert db.engine.url.database == ':memory:'

    with application.app_context():
        assert_test_database()
        try:
            yield application
        finally:
            # Check the bound engine, not just the displayed config, before cleanup.
            assert_test_database()
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """创建认证头"""
    # 注册测试用户
    response = client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123!'
    })
    
    # 登录获取token
    response = client.post('/api/auth/login', json={
        'username': 'test@example.com',
        'password': 'TestPass123!'
    })
    
    token = response.json['data']['tokens']['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_knowledge_data():
    """示例知识库数据"""
    return {
        'title': '测试知识条目',
        'content': '这是一个测试知识条目的内容',
        'source_url': 'https://example.com',
        'source_type': 'web',
        'category': '测试分类',
        'tags': ['测试', '示例']
    }


@pytest.fixture(autouse=True)
def mock_email_service():
    """自动Mock邮件服务"""
    with patch('Backend.services.email_service.EmailService.send_email', autospec=True) as mock_send_email:
        mock_send_email.return_value = True
        from Backend.services.email_verification_service import EmailService
        assert EmailService.send_email is mock_send_email
        yield mock_send_email
