"""
JWT工具类
"""
from datetime import datetime, timedelta, timezone
import jwt
from flask import current_app


def create_access_token(user_id):
    """创建访问令牌"""
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'token_type': 'access',
        'exp': now + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        'iat': now,
        'jti': f"{user_id}_{now.timestamp()}_{id(now)}"  # 添加唯一标识符
    }
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )


def create_refresh_token(user_id):
    """创建刷新令牌"""
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'token_type': 'refresh',
        'exp': now + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
        'iat': now,
        'jti': f"refresh_{user_id}_{now.timestamp()}_{id(now)}"  # 添加唯一标识符
    }
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )


def verify_token(token):
    """验证令牌"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=[current_app.config['JWT_ALGORITHM']]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError('Token已过期')
    except jwt.InvalidTokenError:
        raise ValueError('无效的Token')


def decode_token(token):
    """
    解码令牌（不验证过期时间）
    用于获取token信息，即使token已过期
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=[current_app.config['JWT_ALGORITHM']],
            options={"verify_exp": False}  # 不验证过期时间
        )
        return payload
    except jwt.InvalidTokenError:
        raise ValueError('无效的Token')