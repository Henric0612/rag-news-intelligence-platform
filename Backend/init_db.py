"""
数据库初始化脚本
"""
import sys
from pathlib import Path

# 确保可以导入Backend包
backend_parent = Path(__file__).parent.parent
if str(backend_parent) not in sys.path:
    sys.path.insert(0, str(backend_parent))

from Backend.app import create_app
from Backend.models import db
from Backend.models.user import User


def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        try:
            # 删除所有表
            print("删除现有表...")
            db.drop_all()
            
            # 创建所有表
            print("创建数据库表...")
            db.create_all()
            
            # 创建管理员用户
            print("创建管理员用户...")
            admin = User(
                username='admin',
                email='admin@xu-news.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            
            # 创建测试用户
            print("创建测试用户...")
            test_user = User(
                username='testuser',
                email='test@xu-news.com',
                role='user',
                is_active=True
            )
            test_user.set_password('test123')
            
            db.session.add(admin)
            db.session.add(test_user)
            db.session.commit()
            
            print("数据库初始化完成!")
            print("\n默认账户信息:")
            print("管理员 - 用户名: admin, 密码: admin123")
            print("测试用户 - 用户名: testuser, 密码: test123")
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    init_database()
