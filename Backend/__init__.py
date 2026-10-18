"""
Backend 应用包初始化

RAG News Intelligence Platform 后端服务包
"""

# 导出主要接口
from .app import create_app
from .version import get_build_info

__version__ = get_build_info()['version']

__all__ = [
    'create_app',
    'app',
    'config',
    'models',
    'routes',
    'services',
    'utils',
]
