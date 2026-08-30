"""
RAG News Intelligence Platform 后端配置文件
"""
import os
from datetime import timedelta
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('RAG_DATA_DIR', BASE_DIR / "data")).expanduser().resolve()
SQLITE_DIR = DATA_DIR / "sqlite"
FAISS_DIR = DATA_DIR / "faiss"
UPLOADS_DIR = DATA_DIR / "uploads"

# 延迟创建目录 - 只在真正需要时创建
def ensure_directories():
    """确保必要的目录存在"""
    for directory in [DATA_DIR, SQLITE_DIR, FAISS_DIR, UPLOADS_DIR]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)


class Config:
    """基础配置"""
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # ===== 模型配置 - 使用本地离线模型环境 =====
    # 本地模型缓存路径
    MODEL_CACHE_DIR = os.path.expanduser(os.environ.get('MODEL_CACHE_DIR', '~/.cache/huggingface/hub'))
    
    # HuggingFace 离线模式配置（官方推荐）
    # 参考: https://huggingface.co/docs/transformers/installation#offline-mode
    HF_HUB_OFFLINE = True                    # 强制离线模式
    TRANSFORMERS_OFFLINE = True              # Transformers 离线模式
    HF_HUB_DISABLE_TELEMETRY = True          # 禁用遥测数据收集
    HF_DATASETS_OFFLINE = True               # Datasets 离线模式（如果使用）
    
    # LangChain 模型配置 - 强制使用本地文件
    LANGCHAIN_MODEL_LOCAL_FILES_ONLY = True  # LangChain 强制本地模式
    
    # 数据库配置 - 使用绝对路径确保自动重启兼容性
    # 确保路径在所有进程中都是一致的
    _db_path = str(SQLITE_DIR.resolve() / "knowledge.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{_db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # SQLAlchemy连接池配置 - SQLite开发环境优化
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # 连接前测试连接是否有效
        'pool_recycle': 300,    # 连接回收时间（5分钟）
        'pool_size': 5,         # 增加连接池大小以支持并发请求
        'max_overflow': 10,     # 允许额外的溢出连接
        'pool_timeout': 30,     # 增加获取连接超时时间
        'pool_reset_on_return': 'commit',  # 返回连接时重置
        'connect_args': {
            'check_same_thread': False,  # 允许多线程访问
            'timeout': 30                # 连接超时时间（秒）
        }
    }
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # ✅ 改为1小时（主流安全实践）
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = 'HS256'
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_IDENTITY_CLAIM = 'user_id'  # 使用user_id作为身份标识字段
    
    # CORS配置
    CORS_ORIGINS = [
        origin.strip() for origin in os.environ.get(
            'CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000'
        ).split(',') if origin.strip()
    ]
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
    UPLOAD_FOLDER = str(UPLOADS_DIR)
    
    # Redis配置
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Celery配置
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # AI模型配置 - 使用本地模型
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    RERANK_MODEL = os.environ.get('RERANK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'qwen3:8b')
    
    # Ollama配置 - 使用本地Ollama服务
    OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
    
    # FAISS配置
    FAISS_INDEX_PATH = os.environ.get('FAISS_INDEX_PATH', str(FAISS_DIR / "knowledge.index"))
    FAISS_ID_MAPPING_PATH = os.environ.get('FAISS_ID_MAPPING_PATH', str(FAISS_DIR / "id_mapping.json"))
    VECTOR_DIMENSION = 384
    
    # 文本处理配置
    MAX_TEXT_LENGTH = int(os.environ.get('MAX_TEXT_LENGTH', 512))
    
    # 搜索配置
    SEARCH_CACHE_ENABLED = os.environ.get('SEARCH_CACHE_ENABLED', 'true').lower() == 'true'
    SEARCH_CACHE_TTL = int(os.environ.get('SEARCH_CACHE_TTL', 3600))
    
    # RAG配置
    RAG_DEFAULT_TOP_K = int(os.environ.get('RAG_DEFAULT_TOP_K', 20))
    RAG_RERANK_TOP_K = int(os.environ.get('RAG_RERANK_TOP_K', 5))
    RAG_MAX_CONTEXT_LENGTH = int(os.environ.get('RAG_MAX_CONTEXT_LENGTH', 4000))
    RAG_ENABLE_RERANK = os.environ.get('RAG_ENABLE_RERANK', 'true').lower() == 'true'
    RAG_ENABLE_WEB_FALLBACK = os.environ.get('RAG_ENABLE_WEB_FALLBACK', 'false').lower() == 'true'
    
    # LLM配置
    LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS', 2048))
    LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', 0.7))
    
    # 爬虫配置
    CRAWLER_USER_AGENT = 'Mozilla/5.0 (compatible; RAG-News-Intelligence-Bot/1.0)'
    CRAWLER_TIMEOUT = 30
    CRAWLER_MAX_RETRIES = 3
    CRAWLER_DELAY_BETWEEN_REQUESTS = 1  # 请求间延迟（秒）
    
    # RSS内容质量配置
    RSS_MIN_CONTENT_LENGTH = int(os.environ.get('RSS_MIN_CONTENT_LENGTH', 200))  # 最小内容长度阈值
    RSS_ENABLE_FULL_TEXT_FETCH = os.environ.get('RSS_ENABLE_FULL_TEXT_FETCH', 'true').lower() == 'true'  # 启用完整文本抓取
    RSS_FULL_TEXT_FETCH_TIMEOUT = int(os.environ.get('RSS_FULL_TEXT_FETCH_TIMEOUT', 15))  # 完整文本抓取超时
    RSS_SHORT_PAGE_THRESHOLD = int(os.environ.get('RSS_SHORT_PAGE_THRESHOLD', 150))  # 短页面判断阈值（避免过度爬取）
    
    # 邮件配置
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@rag-news-intelligence-platform.local')
    FROM_NAME = os.environ.get('FROM_NAME', 'RAG News Intelligence Platform')
    
    # 前端URL配置
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # 关闭SQL日志，减少启动时间
    
    # 开发环境SQLite优化配置 - 专门针对Flask自动重启优化
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # 连接前测试连接是否有效
        'pool_recycle': 900,    # 连接回收时间（15分钟，更频繁回收）
        'pool_size': 5,         # 增加连接池大小以支持并发请求
        'max_overflow': 10,     # 允许额外的溢出连接
        'pool_timeout': 30,     # 增加获取连接超时时间
        'connect_args': {
            'check_same_thread': False,  # 允许多线程访问
            'timeout': 30                # 增加连接超时时间
        }
    }


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # 生产环境应该从环境变量读取敏感配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # 测试环境SQLite配置 - 内存数据库
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # 连接前测试连接是否有效
        'connect_args': {
            'check_same_thread': False,  # 允许多线程访问
        }
    }
    
    # 测试环境强制离线模型配置
    EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
    RERANK_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    LLM_MODEL = 'qwen3:8b'
    
    # 测试环境模型配置
    USE_LOCAL_MODELS = True
    
    # 本地模型缓存路径
    MODEL_CACHE_DIR = os.path.expanduser('~/.cache/huggingface/hub')
    
    # 测试时禁用网络请求
    CRAWLER_TIMEOUT = 0  # 测试时禁用爬虫
    RAG_ENABLE_WEB_FALLBACK = False  # 测试时禁用网络回退


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
