"""
认证路由
"""
from flask import Blueprint, request
from Backend.services.auth_service import AuthService
from Backend.services.password_reset_service import PasswordResetService
from Backend.services.account_security_service import AccountSecurityService
from Backend.services.email_verification_service import EmailVerificationService
from Backend.utils.response import success_response, error_response
from Backend.utils.decorators import jwt_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['username', 'password', 'email']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'缺少必填字段: {field}', 400)
    
    try:
        # 注册用户
        user = AuthService.register_user(
            username=data['username'],
            password=data['password'],
            email=data['email']
        )
        
        # 生成令牌
        tokens = AuthService.generate_tokens(user.id)
        
        return success_response({
            'user': user.to_dict(),
            'tokens': tokens
        }, message='注册成功', code=201)
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'注册失败: {str(e)}', 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    # 验证必填字段
    if not data.get('username') or not data.get('password'):
        return error_response('用户名和密码不能为空', 400)
    
    try:
        # 验证用户
        user = AuthService.authenticate_user(
            username=data['username'],
            password=data['password']
        )
        
        # 生成令牌
        tokens = AuthService.generate_tokens(user.id)
        
        return success_response({
            'user': user.to_dict(),
            'tokens': tokens
        }, message='登录成功')
        
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        return error_response(f'登录失败: {str(e)}', 500)


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    try:
        user = AuthService.get_user_by_id(request.current_user_id)
        
        if not user:
            return error_response('用户不存在', 404)
        
        return success_response({'user': user.to_dict()})
        
    except Exception as e:
        return error_response(f'获取用户信息失败: {str(e)}', 500)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    """刷新访问令牌"""
    try:
        # 获取当前用户ID
        user_id = request.current_user_id
        
        # 验证用户是否存在且活跃
        user = AuthService.get_user_by_id(user_id)
        if not user or not user.is_active:
            return error_response('用户不存在或已被禁用', 401)
        
        # 生成新的访问令牌
        tokens = AuthService.generate_tokens(user_id)
        
        return success_response({
            'tokens': tokens
        }, message='令牌刷新成功')
        
    except Exception as e:
        return error_response(f'令牌刷新失败: {str(e)}', 500)


@auth_bp.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    """请求密码重置"""
    data = request.get_json()
    
    # 验证必填字段
    if not data.get('email'):
        return error_response('邮箱地址不能为空', 400)
    
    try:
        success, message = PasswordResetService.request_password_reset(data['email'])
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 400)
            
    except Exception as e:
        return error_response(f'请求密码重置失败: {str(e)}', 500)


@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """验证重置令牌"""
    data = request.get_json()
    
    # 验证必填字段
    if not data.get('token'):
        return error_response('重置令牌不能为空', 400)
    
    try:
        is_valid, message, user = PasswordResetService.verify_reset_token(data['token'])
        
        if is_valid:
            return success_response({
                'valid': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }, message=message)
        else:
            return error_response(message, 400)
            
    except Exception as e:
        return error_response(f'验证重置令牌失败: {str(e)}', 500)


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['token', 'password']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'缺少必填字段: {field}', 400)
    
    try:
        success, message = PasswordResetService.reset_password(
            token=data['token'],
            new_password=data['password']
        )
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 400)
            
    except Exception as e:
        return error_response(f'重置密码失败: {str(e)}', 500)


@auth_bp.route('/login-history', methods=['GET'])
@jwt_required()
def get_login_history():
    """获取用户登录历史"""
    try:
        user_id = request.current_user_id
        limit = request.args.get('limit', 50, type=int)
        
        history = AccountSecurityService.get_login_history(user_id, limit)
        
        return success_response(history)
        
    except Exception as e:
        return error_response(f'获取登录历史失败: {str(e)}', 500)


@auth_bp.route('/security-stats', methods=['GET'])
@jwt_required()
def get_security_stats():
    """获取安全统计信息"""
    try:
        stats = AccountSecurityService.get_security_stats()
        return success_response(stats)
        
    except Exception as e:
        return error_response(f'获取安全统计失败: {str(e)}', 500)


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """验证邮箱"""
    data = request.get_json()
    
    # 验证必填字段
    if not data.get('token'):
        return error_response('验证令牌不能为空', 400)
    
    try:
        success, message, user = EmailVerificationService.verify_email(data['token'])
        
        if success:
            return success_response({
                'user': user.to_dict()
            }, message=message)
        else:
            return error_response(message, 400)
            
    except Exception as e:
        return error_response(f'验证邮箱失败: {str(e)}', 500)


@auth_bp.route('/resend-verification', methods=['POST'])
@jwt_required()
def resend_verification():
    """重新发送验证邮件"""
    try:
        user_id = request.current_user_id
        success, message = EmailVerificationService.resend_verification_email(user_id)
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 400)
            
    except Exception as e:
        return error_response(f'重新发送验证邮件失败: {str(e)}', 500)


@auth_bp.route('/cleanup-logs', methods=['POST'])
@jwt_required()
def cleanup_logs():
    """清理旧日志（管理员功能）"""
    try:
        # 这里应该检查用户权限，暂时跳过
        days = request.json.get('days', 30) if request.is_json else 30
        
        AccountSecurityService.cleanup_old_logs(days)
        AccountSecurityService.unlock_expired_accounts()
        EmailVerificationService.cleanup_expired_tokens()
        
        return success_response(message='日志清理完成')
        
    except Exception as e:
        return error_response(f'清理日志失败: {str(e)}', 500)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出（将token加入黑名单）"""
    from Backend.services.token_blacklist_service import TokenBlacklistService
    from Backend.utils.jwt_utils import decode_token
    from datetime import datetime, timezone
    
    try:
        # 获取当前token
        token = request.current_token
        
        # 解码token获取过期时间
        try:
            payload = decode_token(token)
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            else:
                expires_at = None
        except Exception:
            expires_at = None
        
        # ✅ 将token加入黑名单
        TokenBlacklistService.add_to_blacklist(token, expires_at)
        
        return success_response(message='登出成功')
    except Exception as e:
        # 即使加入黑名单失败，也返回成功（客户端会清除本地token）
        import logging
        logging.getLogger(__name__).error(f'登出时加入黑名单失败: {str(e)}')
        return success_response(message='登出成功')
