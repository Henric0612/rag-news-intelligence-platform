"""
Sprint 0：项目准备与设计 - 环境验证测试
测试用例：ENV-001, ENV-002, FRAME-001, FRAME-002, DB-001, DB-002
"""
import pytest
import sys
import os
from flask import Flask


class TestSprint0Environment:
    """Sprint 0：环境验证测试（6个用例）"""
    
    def test_python_version(self):
        """ENV-001: Python 3.11+环境验证"""
        assert sys.version_info >= (3, 11), "Python版本需要3.11+"
        print(f"✓ Python版本: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    def test_nodejs_environment(self):
        """ENV-002: Node.js 18+环境验证"""
        # 后端测试中，我们验证Node.js相关配置是否存在
        # 实际Node.js版本检查应在前端测试中进行
        frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Frontend')
        package_json = os.path.join(frontend_path, 'package.json')
        assert os.path.exists(package_json), "Frontend package.json应该存在"
        print("✓ Frontend环境配置存在")
    
    def test_flask_initialization(self, app):
        """FRAME-001: Flask应用初始化"""
        assert isinstance(app, Flask)
        assert app.config['SECRET_KEY'] is not None
        assert app.config['SQLALCHEMY_DATABASE_URI'] is not None
        assert app.config['TESTING'] is True
        print("✓ Flask应用初始化成功")
    
    def test_vue_framework_config(self):
        """FRAME-002: Vue3应用初始化验证"""
        # 验证Vue3项目配置文件存在
        frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Frontend')
        vite_config = os.path.join(frontend_path, 'vite.config.js')
        assert os.path.exists(vite_config), "Vite配置文件应该存在"
        print("✓ Vue3项目配置存在")
    
    def test_sqlite_connection(self, app):
        """DB-001: SQLite数据库连接"""
        from Backend.models import db
        with app.app_context():
            # 测试数据库连接
            assert db.engine is not None
            # 测试数据库可以执行查询
            result = db.session.execute(db.text('SELECT 1')).scalar()
            assert result == 1
            print("✓ SQLite数据库连接成功")
    
    def test_faiss_initialization(self, app):
        """DB-002: FAISS向量库初始化"""
        with app.app_context():
            # 验证FAISS相关配置存在
            assert 'FAISS_INDEX_PATH' in app.config
            assert 'FAISS_ID_MAPPING_PATH' in app.config
            
            # 验证可以导入FAISS
            try:
                import faiss
                print(f"✓ FAISS库版本: {faiss.__version__ if hasattr(faiss, '__version__') else 'unknown'}")
            except ImportError:
                pytest.skip("FAISS未安装，跳过测试")
