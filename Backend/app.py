"""
XU-News-AI-RAG backend main app
"""
import os
import warnings
import logging
import time

# ===== warning filters =====
# suppress noisy warnings from third-party libraries
warnings.filterwarnings('ignore', category=UserWarning, module='jieba')
warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='transformers')

# set logging levels for third-party libraries
logging.getLogger('jieba').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

# ===== HuggingFace offline mode (official) =====
# must be set before importing transformers/langchain
# ref: https://huggingface.co/docs/transformers/installation#offline-mode
os.environ['TRANSFORMERS_OFFLINE'] = '1'           # transformers offline
os.environ['HF_HUB_OFFLINE'] = '1'                 # hf hub offline
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'       # disable telemetry
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'   # disable progress bars
os.environ['HF_DATASETS_OFFLINE'] = '1'            # datasets offline (if used)
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'  # disable advisory warnings

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import atexit
import signal
import sys


def validate_model_config(app):
    """Validate model configuration"""
    required_configs = [
        ('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
        ('RERANK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2'),
        ('LLM_MODEL', 'qwen3:8b')
    ]
    
    for key, expected_value in required_configs:
        if not app.config.get(key):
            print(f"Warning: {key} not set, using default")


def show_model_info(app):
    """Show model configuration (lazy output)"""
    print(f"Embedding model: {app.config.get('EMBEDDING_MODEL')}")
    print(f"Rerank model: {app.config.get('RERANK_MODEL')}")
    print(f"LLM model: {app.config.get('LLM_MODEL')}")
    print(f"Ollama host: {app.config.get('OLLAMA_HOST')}")
    print(f"Model cache dir: {app.config.get('MODEL_CACHE_DIR')}")


def create_app(config_name=None):
    """Application factory"""
    # startup timing
    app_start_time = time.time()
    
    # detect reloader child process
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if not is_reloader_process:
        print("\n" + "="*80)
        print("XU-News-AI-RAG starting...")
        print("="*80)
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Step 1: load config
    if not is_reloader_process:
        print("[1/4] Loading config...", end=" ")
    
    from .config import config
    from .models import db
    from .db_init import cleanup_database_connections, ensure_database_directory
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    if not is_reloader_process:
        print("OK")
    
    # Step 2: init components
    if not is_reloader_process:
        print("[2/4] Initializing components (Flask, CORS, JWT)...", end=" ")
    
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    if not is_reloader_process:
        print("OK")
    
    # Step 3: register routes
    if not is_reloader_process:
        print("[3/4] Registering routes (8 blueprints)...", end=" ")
    
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
        print("OK")
    
    # Database connection health check
    @app.before_request
    def ensure_database_connection():
        """Ensure database connection is healthy"""
        try:
            # Test DB connection
            db.session.execute(db.text('SELECT 1'))
        except Exception as e:
            print(f"DB connection check failed: {e}")
            # Try to recover DB connection
            try:
                # Rollback any pending transaction
                db.session.rollback()
                # Remove current session
                db.session.remove()
                # Dispose engine (without re-init app)
                db.engine.dispose()
                print("DB connection reset")
            except Exception as reconnect_error:
                print(f"DB connection reset failed: {reconnect_error}")
                # If still failing, return error
                from .utils.response import error_response
                return error_response('Database connection failed', 500)
    
    # Teardown
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Cleanup SQLAlchemy session after request"""
        try:
            if exception:
                db.session.rollback()
            db.session.remove()
        except Exception as e:
            print(f"Cleanup session failed: {e}")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        from .utils.response import error_response
        return error_response('Resource not found', 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        from .utils.response import error_response
        db.session.rollback()
        return error_response('Internal server error', 500)
    
    # Step 4: init database
    if not is_reloader_process:
        print("[4/4] Initializing database...", end=" ")
    
    try:
        # Ensure necessary directories exist
        from .config import ensure_directories
        ensure_directories()
        
        with app.app_context():
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            ensure_database_directory(db_uri)
            
            # Test DB connection
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
            except Exception as conn_error:
                # Try to recreate DB connection
                db.engine.dispose()
                db.init_app(app)
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
            
            # Create tables if not exists
            db.create_all()
            
            # SQLite pragmas
            with db.engine.connect() as conn:
                conn.execute(db.text('PRAGMA journal_mode=DELETE'))
                conn.execute(db.text('PRAGMA synchronous=NORMAL'))
                conn.execute(db.text('PRAGMA cache_size=-32000'))
                conn.execute(db.text('PRAGMA foreign_keys=ON'))
                conn.execute(db.text('PRAGMA busy_timeout=10000'))
        
        if not is_reloader_process:
            print("OK")
    except Exception as e:
        if not is_reloader_process:
            print(f"FAIL\n   Warning: DB init failed ({e})")
    
    # Validate model config
    with app.app_context():
        validate_model_config(app)
    
    # Lazy show model info on first request
    @app.after_request
    def show_model_info_on_first_request(response):
        if not hasattr(app, '_model_info_shown'):
            if not is_reloader_process:
                print("\nModel config:")
                print(f"   - Embedding model: {app.config.get('EMBEDDING_MODEL')}")
                print(f"   - Rerank model: {app.config.get('RERANK_MODEL')}")
                print(f"   - LLM model: {app.config.get('LLM_MODEL')} @ {app.config.get('OLLAMA_HOST')}")
            app._model_info_shown = True
        return response
    
    # Startup summary
    app_init_time = time.time() - app_start_time
    
    if not is_reloader_process:
        print("\n" + "="*80)
        print(f"App initialized. Elapsed: {app_init_time:.2f}s")
        print("="*80 + "\n")
    
    # store startup time in app config
    app.config['APP_INIT_TIME'] = app_init_time
    
    return app


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    print(f"\nReceived signal {signum}, shutting down...")
    print("Application shutting down...")
    sys.exit(0)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Error: running app.py directly is not supported")
    print("="*60)
    print("\nUse module mode to run the app:")
    print("\n   Method 1 (recommended):")
    print("   cd project root")
    print("   python -m Backend")
    print("\n   Method 2:")
    print("   cd Backend")
    print("   python -m Backend")
    print("\nTip: why module mode?")
    print("   - Supports relative imports (from .config import config)")
    print("   - Proper package path resolution")
    print("   - Consistent test and production environment")
    print("="*60 + "\n")
    sys.exit(1)
