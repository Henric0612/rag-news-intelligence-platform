"""
XU-News-AI-RAG 后端主应用
"""
import os
import warnings
import logging
import time

# ===== 警告屏蔽配置 =====
# 屏蔽第三方库的无关警告
warnings.filterwarnings('ignore', category=UserWarning, module='jieba')
warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='transformers')

# 设置日志级别，减少第三方库的警告输出
logging.getLogger('jieba').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

# ===== HuggingFace 离线模式配置（官方推荐） =====
# 必须在导入任何 transformers/langchain 库之前设置
# 参考: https://huggingface.co/docs/transformers/installation#offline-mode
os.environ['TRANSFORMERS_OFFLINE'] = '1'           # Transformers 离线模式
os.environ['HF_HUB_OFFLINE'] = '1'                 # HuggingFace Hub 离线模式
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'       # 禁用遥测数据收集
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'   # 禁用进度条（减少日志输出）
os.environ['HF_DATASETS_OFFLINE'] = '1'            # Datasets 离线模式（如果使用）
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'  # 禁用 transformers advisory 警告

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import atexit
import signal
import sys


def validate_model_config(app):
    """验证模型配置"""
    required_configs = [
        ('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
        ('RERANK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2'),
        ('LLM_MODEL', 'qwen3:8b')
    ]
    
    for key, expected_value in required_configs:
        if not app.config.get(key):
            print(f"警告: {key} 未配置，使用默认值")


def show_model_info(app):
    """显示模型配置信息（延迟显示）"""
    print(f"嵌入模型: {app.config.get('EMBEDDING_MODEL')}")
    print(f"重排模型: {app.config.get('RERANK_MODEL')}")
    print(f"LLM模型: {app.config.get('LLM_MODEL')}")
    print(f"Ollama主机: {app.config.get('OLLAMA_HOST')}")
    print(f"模型缓存目录: {app.config.get('MODEL_CACHE_DIR')}")


def create_app(config_name=None):
    """应用工厂函数"""
    # ✅ 启动性能监控
    app_start_time = time.time()
    
    # 检测是否为reloader子进程
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if not is_reloader_process:
        print("\n" + "="*80)
        print("🚀 XU-News-AI-RAG 启动中...")
        print("="*80)
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # ========== 第1步：加载配置 ==========
    if not is_reloader_process:
        print("[1/4] 📋 加载配置...", end=" ")
    
    from .config import config
    from .models import db
    from .db_init import cleanup_database_connections, ensure_database_directory
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    if not is_reloader_process:
        print("✓")
    
    # ========== 第2步：初始化组件 ==========
    if not is_reloader_process:
        print("[2/4] 🔧 初始化组件 (Flask, CORS, JWT)...", end=" ")
    
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    if not is_reloader_process:
        print("✓")
    
    # ========== 第3步：注册路由 ==========
    if not is_reloader_process:
        print("[3/4] 🛣️  注册路由 (8个蓝图)...", end=" ")
    
    from .routes import health_bp, auth_bp, knowledge_bp, search_bp, rag_bp, crawler_bp, upload_bp
    from .routes.analytics import analytics_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(crawler_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(analytics_bp)
    
    if not is_reloader_process:
        print("✓")
    
    # 数据库连接健康检查
    @app.before_request
    def ensure_database_connection():
        """确保数据库连接正常"""
        try:
            # 测试数据库连接
            db.session.execute(db.text('SELECT 1'))
        except Exception as e:
            print(f"数据库连接检查失败: {e}")
            # 尝试恢复数据库连接
            try:
                # 回滚任何挂起的事务
                db.session.rollback()
                # 移除当前session
                db.session.remove()
                # 清理连接池（不重新初始化app）
                db.engine.dispose()
                print("数据库连接已重置")
            except Exception as reconnect_error:
                print(f"数据库连接重置失败: {reconnect_error}")
                # 如果重置失败，返回错误响应
                from .utils.response import error_response
                return error_response('数据库连接失败', 500)
    
    # 请求后清理
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """请求结束后清理数据库session"""
        try:
            if exception:
                db.session.rollback()
            db.session.remove()
        except Exception as e:
            print(f"清理session失败: {e}")
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        from .utils.response import error_response
        return error_response('资源不存在', 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        from .utils.response import error_response
        db.session.rollback()
        return error_response('服务器内部错误', 500)
    
    # ========== 第4步：初始化数据库 ==========
    if not is_reloader_process:
        print("[4/4] 🗄️  初始化数据库...", end=" ")
    
    try:
        # 确保必要的目录存在
        from .config import ensure_directories
        ensure_directories()
        
        with app.app_context():
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            ensure_database_directory(db_uri)
            
            # 测试数据库连接
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
            except Exception as conn_error:
                # 尝试重新创建数据库连接
                db.engine.dispose()
                db.init_app(app)
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
            
            # 创建表（如果不存在）
            db.create_all()
            
            # 设置SQLite参数
            with db.engine.connect() as conn:
                conn.execute(db.text('PRAGMA journal_mode=DELETE'))
                conn.execute(db.text('PRAGMA synchronous=NORMAL'))
                conn.execute(db.text('PRAGMA cache_size=-32000'))
                conn.execute(db.text('PRAGMA foreign_keys=ON'))
                conn.execute(db.text('PRAGMA busy_timeout=10000'))
        
        if not is_reloader_process:
            print("✓")
    except Exception as e:
        if not is_reloader_process:
            print(f"✗\n   ⚠️  警告: 数据库初始化失败 ({e})")
    
    # 模型配置验证
    with app.app_context():
        validate_model_config(app)
    
    # 延迟显示模型信息 - 在第一次请求后显示
    @app.after_request
    def show_model_info_on_first_request(response):
        if not hasattr(app, '_model_info_shown'):
            if not is_reloader_process:
                print("\n📦 模型配置:")
                print(f"   • 嵌入模型: {app.config.get('EMBEDDING_MODEL')}")
                print(f"   • 重排模型: {app.config.get('RERANK_MODEL')}")
                print(f"   • LLM模型: {app.config.get('LLM_MODEL')} @ {app.config.get('OLLAMA_HOST')}")
            app._model_info_shown = True
        return response
    
    # ✅ 启动完成摘要
    app_init_time = time.time() - app_start_time
    
    if not is_reloader_process:
        print("\n" + "="*80)
        print(f"✅ 应用初始化完成！耗时: {app_init_time:.2f}秒")
        print("="*80 + "\n")
    
    # 存储启动时间到应用配置
    app.config['APP_INIT_TIME'] = app_init_time
    
    return app


def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭"""
    print(f"\n收到信号 {signum}，正在关闭应用...")
    print("应用正在关闭...")
    sys.exit(0)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("❌ 错误：不支持直接运行 app.py")
    print("="*60)
    print("\n✅ 请使用模块模式运行应用：")
    print("\n   方式1（推荐）：")
    print("   cd 项目根目录")
    print("   python -m Backend")
    print("\n   方式2：")
    print("   cd Backend目录")
    print("   python -m Backend")
    print("\n💡 为什么？")
    print("   - 支持相对导入（from .config import config）")
    print("   - 正确的包路径解析")
    print("   - 测试和生产环境一致")
    print("="*60 + "\n")
    sys.exit(1)
