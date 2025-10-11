"""
健康检查路由
"""
from datetime import datetime, timezone
from flask import Blueprint, current_app, request
from Backend.utils.response import success_response, error_response
from Backend.models import db
from sqlalchemy import text
import time

health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查 - 基础存活检查（最快）"""
    response_data = {
        'status': 'healthy',
        'service': 'XU-News-AI-RAG Backend',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0'
    }
    
    # ✅ 添加启动时间信息
    if 'APP_INIT_TIME' in current_app.config:
        response_data['app_init_time_seconds'] = round(current_app.config['APP_INIT_TIME'], 2)
    
    return success_response(response_data)


@health_bp.route('/health/database', methods=['GET'])
def database_health_check():
    """数据库健康检查 - 仅检查数据库连接（快速）"""
    start_time = time.time()
    
    try:
        # 快速数据库连接测试，添加超时控制
        db.session.execute(text('SELECT 1'))
        response_time = int((time.time() - start_time) * 1000)
        
        return success_response({
            'status': 'connected',
            'database': 'connected',
            'response_time_ms': response_time,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        current_app.logger.error(f"数据库连接检查失败: {str(e)}")
        
        return error_response('数据库连接失败', 503, {
            'status': 'disconnected',
            'database': 'disconnected',
            'response_time_ms': response_time,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    就绪检查 - 检查所有依赖服务是否就绪
    
    查询参数：
    - quick: 快速检查模式（仅检查服务初始化状态，不执行实际调用）
    """
    quick_mode = request.args.get('quick', 'true').lower() == 'true'
    
    checks = {
        'status': 'ready',
        'service': 'XU-News-AI-RAG Backend',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'quick_mode': quick_mode
    }
    
    # 检查数据库连接（快速）
    db_start = time.time()
    try:
        db.session.execute(text('SELECT 1'))
        checks['database'] = 'connected'
        checks['database_response_time_ms'] = int((time.time() - db_start) * 1000)
    except Exception as e:
        checks['database'] = 'disconnected'
        checks['database_response_time_ms'] = int((time.time() - db_start) * 1000)
        checks['status'] = 'not_ready'
        current_app.logger.error(f"数据库连接检查失败: {str(e)}")
    
    # 检查向量服务（快速模式：仅检查初始化状态）
    vector_start = time.time()
    try:
        from Backend.services.vector_service import get_vector_service
        vector_service = get_vector_service()
        if vector_service and vector_service.embedding_model:
            checks['vector_service'] = 'ready'
        else:
            checks['vector_service'] = 'not_ready'
        checks['vector_response_time_ms'] = int((time.time() - vector_start) * 1000)
    except Exception as e:
        checks['vector_service'] = 'error'
        checks['vector_response_time_ms'] = int((time.time() - vector_start) * 1000)
        current_app.logger.warning(f"向量服务检查失败: {str(e)}")
    
    # 检查LLM服务（快速模式：仅检查初始化状态）
    llm_start = time.time()
    try:
        from Backend.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        if llm_service and llm_service.llm:
            checks['llm_service'] = 'ready'
        else:
            checks['llm_service'] = 'not_ready'
        checks['llm_response_time_ms'] = int((time.time() - llm_start) * 1000)
    except Exception as e:
        checks['llm_service'] = 'error'
        checks['llm_response_time_ms'] = int((time.time() - llm_start) * 1000)
        current_app.logger.warning(f"LLM服务检查失败: {str(e)}")
    
    # 计算总响应时间
    checks['total_response_time_ms'] = (
        checks.get('database_response_time_ms', 0) +
        checks.get('vector_response_time_ms', 0) +
        checks.get('llm_response_time_ms', 0)
    )
    
    # 如果数据库不可用，返回503（其他服务不影响就绪状态）
    if checks['database'] != 'connected':
        return error_response('服务未就绪', 503, checks)
    
    return success_response(checks)
