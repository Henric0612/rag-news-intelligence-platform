"""
Backend 应用包初始化

XU-News-AI-RAG 后端服务包
"""

# 导出主要接口
from .app import create_app

__version__ = '1.0.0'

__all__ = [
    'create_app',
    'app',
    'config',
    'models',
    'routes',
    'services',
    'utils',
]

