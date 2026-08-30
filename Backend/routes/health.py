"""Health and readiness endpoints."""
from datetime import datetime, timezone
import time

import requests
from flask import Blueprint, current_app, request
from sqlalchemy import text

from Backend.models import db
from Backend.utils.response import error_response, success_response


health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Process liveness. External AI failures must not change this response."""
    response_data = {
        'status': 'healthy',
        'service': 'RAG News Intelligence Platform Backend',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0'
    }
    if 'APP_INIT_TIME' in current_app.config:
        response_data['app_init_time_seconds'] = round(current_app.config['APP_INIT_TIME'], 2)
    return success_response(response_data)


@health_bp.route('/health/database', methods=['GET'])
def database_health_check():
    """Check only the database connection."""
    start_time = time.time()
    try:
        db.session.execute(text('SELECT 1'))
        return success_response({
            'status': 'connected',
            'database': 'connected',
            'response_time_ms': int((time.time() - start_time) * 1000),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as exc:
        current_app.logger.error("Database health check failed: %s", exc)
        return error_response('数据库连接失败', 503, {
            'status': 'disconnected',
            'database': 'disconnected',
            'response_time_ms': int((time.time() - start_time) * 1000),
            'error': str(exc),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Quick checks DB/config; full mode also verifies every required AI dependency."""
    started_at = time.time()
    quick_mode = request.args.get('quick', 'true').lower() == 'true'
    checks = {
        'status': 'ready',
        'service': 'RAG News Intelligence Platform Backend',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'quick_mode': quick_mode,
    }

    try:
        db_started_at = time.time()
        db.session.execute(text('SELECT 1'))
        checks['database'] = 'connected'
        checks['database_response_time_ms'] = int((time.time() - db_started_at) * 1000)
    except Exception as exc:
        checks['database'] = 'disconnected'
        checks['database_error'] = str(exc)
        current_app.logger.error("Readiness database check failed: %s", exc)

    from Backend.config import DATA_DIR
    checks['data_directory'] = str(DATA_DIR)
    checks['database_uri_configured'] = bool(current_app.config.get('SQLALCHEMY_DATABASE_URI'))

    if not quick_mode:
        ai_started_at = time.time()
        try:
            from Backend.services.vector_service import get_vector_service
            embedding = getattr(get_vector_service(), 'embedding_model', None)
            embedding_class = embedding.__class__.__name__ if embedding else ''
            checks['embedding'] = (
                'ready' if embedding and embedding_class != 'RandomEmbeddings' else 'not_ready'
            )
        except Exception as exc:
            checks['embedding'] = 'error'
            checks['embedding_error'] = str(exc)

        try:
            from Backend.services.search_service import get_search_service
            reranker = getattr(get_search_service(), 'rerank_model', None)
            checks['reranker'] = 'ready' if reranker else 'not_ready'
        except Exception as exc:
            checks['reranker'] = 'error'
            checks['reranker_error'] = str(exc)

        try:
            ollama_host = current_app.config['OLLAMA_HOST'].rstrip('/')
            expected_model = current_app.config['LLM_MODEL']
            response = requests.get(f"{ollama_host}/api/tags", timeout=5)
            response.raise_for_status()
            installed_models = [model.get('name') for model in response.json().get('models', [])]
            checks['ollama'] = 'ready'
            checks['llm_model'] = 'ready' if expected_model in installed_models else 'not_ready'
            checks['expected_llm_model'] = expected_model
        except Exception as exc:
            checks['ollama'] = 'error'
            checks['llm_model'] = 'not_ready'
            checks['ollama_error'] = str(exc)

        checks['ai_response_time_ms'] = int((time.time() - ai_started_at) * 1000)

    required_checks = ['database']
    if not quick_mode:
        required_checks.extend(['embedding', 'reranker', 'ollama', 'llm_model'])
    checks['total_response_time_ms'] = int((time.time() - started_at) * 1000)

    if (
        not checks['database_uri_configured']
        or any(checks.get(name) not in ('connected', 'ready') for name in required_checks)
    ):
        checks['status'] = 'not_ready'
        return error_response('服务未就绪', 503, checks)

    return success_response(checks)
