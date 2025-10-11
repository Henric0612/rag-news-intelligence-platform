"""
装饰器工具
"""
from functools import wraps
from flask import request
from marshmallow import ValidationError
from .jwt_utils import verify_token
from .response import error_response
from Backend.services.token_blacklist_service import TokenBlacklistService


def jwt_required():
    """JWT认证装饰器（包含黑名单检查）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 添加调试日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"JWT认证检查 - 请求路径: {request.path}")
            
            # 从请求头获取token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logger.error("JWT认证失败: 未提供认证令牌")
                return error_response('未提供认证令牌', 401)
            
            logger.info(f"JWT认证检查 - 找到认证头: {auth_header[:20]}...")
            
            # 解析Bearer token
            try:
                token_type, token = auth_header.split(' ')
                if token_type.lower() != 'bearer':
                    logger.error(f"JWT认证失败: 无效的认证类型 {token_type}")
                    return error_response('无效的认证类型', 401)
            except ValueError:
                logger.error("JWT认证失败: 无效的认证格式")
                return error_response('无效的认证格式', 401)
            
            # ✅ 检查token是否在黑名单中
            if TokenBlacklistService.is_blacklisted(token):
                logger.warning(f"JWT认证失败: Token已被加入黑名单（已登出）")
                return error_response('Token已失效，请重新登录', 401)
            
            # 验证token
            try:
                payload = verify_token(token)
                request.current_user_id = payload['user_id']
                request.current_token = token  # ✅ 保存token供后续使用
                logger.info(f"JWT认证成功 - 用户ID: {payload['user_id']}")
            except ValueError as e:
                logger.error(f"JWT认证失败: {str(e)}")
                return error_response(str(e), 401)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required():
    """管理员权限装饰器"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            from Backend.models import User, db
            
            user = db.session.get(User, request.current_user_id)
            if not user or user.role != 'admin':
                return error_response('需要管理员权限', 403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_json(schema_class):
    """JSON数据验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取JSON数据
            json_data = request.get_json()
            if json_data is None:
                return error_response('请求必须是有效的JSON格式', 400)
            
            # 添加调试日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"收到JSON数据: {json_data}")
            
            # 创建schema实例并验证数据
            try:
                schema = schema_class()
                validated_data = schema.load(json_data)
                # 将验证后的数据添加到request对象中
                request.validated_data = validated_data
                logger.info(f"数据验证成功: {validated_data}")
            except ValidationError as e:
                logger.error(f"数据验证失败: {e.messages}")
                return error_response(f'数据验证失败: {e.messages}', 400)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
