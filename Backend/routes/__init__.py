"""
路由层包
"""
from .auth import auth_bp
from .knowledge import knowledge_bp
from .health import health_bp
from .search import search_bp
from .rag import rag_bp
from .crawler import crawler_bp
from .upload import upload_bp

__all__ = ['auth_bp', 'knowledge_bp', 'health_bp', 'search_bp', 'rag_bp', 'crawler_bp', 'upload_bp']
