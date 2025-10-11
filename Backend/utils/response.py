"""
响应工具类
"""
from datetime import datetime, timezone
from flask import jsonify


def success_response(data=None, message='success', code=200):
    """成功响应"""
    response = {
        'success': True,
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    return jsonify(response), code


def error_response(message='error', code=400, data=None):
    """错误响应"""
    response = {
        'success': False,
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    return jsonify(response), code
