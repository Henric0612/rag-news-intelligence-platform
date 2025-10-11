"""
测试配置和夹具
"""
import os
import sys
from pathlib import Path

import pytest
import tempfile
from unittest.mock import patch

# 确保Backend目录的父目录在Python路径中，以便作为包导入
backend_parent = Path(__file__).parent.parent.parent
if str(backend_parent) not in sys.path:
    sys.path.insert(0, str(backend_parent))

# 使用Backend包导入
from Backend.app import create_app
from Backend.models import db
from Backend.models.user import User


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """全局设置测试环境 - 确保所有测试都使用本地离线模型"""
    # 设置环境变量，强制使用本地模型
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_DATASETS_OFFLINE'] = '1'
    
    print("\n" + "="*60)
    print("测试环境配置 - 本地离线模型模式")
    print("="*60)
    print("[OK] HF_HUB_OFFLINE=1 (禁用HuggingFace Hub联网)")
    print("[OK] TRANSFORMERS_OFFLINE=1 (禁用Transformers联网)")
    print("[OK] HF_DATASETS_OFFLINE=1 (禁用Datasets联网)")
    print("[OK] 模型加载参数: local_files_only=True")
    print("[OK] Ollama配置: 使用本地服务 (http://localhost:11434)")
    print("="*60 + "\n")
    
    yield
    
    # 清理环境变量
    os.environ.pop('HF_HUB_OFFLINE', None)
    os.environ.pop('TRANSFORMERS_OFFLINE', None)
    os.environ.pop('HF_DATASETS_OFFLINE', None)


@pytest.fixture
def app():
    """创建测试应用实例"""
    # 创建临时数据库文件
    db_fd, db_path = tempfile.mkstemp()
    
    # 创建测试应用
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'JWT_SECRET_KEY': 'test-secret-key',
        'CORS_ORIGINS': ['http://localhost:3000'],
        # 邮件配置 - 测试环境
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': 587,
        'SMTP_USERNAME': 'test@example.com',
        'SMTP_PASSWORD': 'testpassword',
        'FROM_EMAIL': 'noreply@test.com',
        'FROM_NAME': 'Test App',
        'FRONTEND_URL': 'http://localhost:3000',
        # 模型配置 - 强制使用本地离线模型
        'USE_LOCAL_MODELS': True,
        'OLLAMA_HOST': 'http://localhost:11434',
        'LLM_MODEL': 'qwen3:8b',
        'EMBEDDING_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
        'RERANK_MODEL': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


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
    with patch('services.email_service.EmailService.send_email') as mock_send_email:
        mock_send_email.return_value = (True, "邮件发送成功")
        yield mock_send_email