"""
Sprint 1：基础设施层 - 数据模型单元测试
测试用例：MODEL-001, MODEL-002, MODEL-003
"""
import pytest
from datetime import datetime
from Backend.models import db
from Backend.models.user import User
from Backend.models.knowledge import KnowledgeItem
from Backend.models.search_history import SearchHistory


class TestSprint1Models:
    """Sprint 1：数据模型测试（3个用例）"""
    
    def test_user_model_crud(self, app):
        """MODEL-001: User模型CRUD"""
        with app.app_context():
            # Create
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()
            
            # Read
            found_user = User.query.filter_by(username='testuser').first()
            assert found_user is not None
            assert found_user.email == 'test@example.com'
            assert found_user.check_password('TestPass123!')
            
            # Update
            found_user.email = 'newemail@example.com'
            db.session.commit()
            updated_user = User.query.filter_by(username='testuser').first()
            assert updated_user.email == 'newemail@example.com'
            
            # Delete
            db.session.delete(updated_user)
            db.session.commit()
            deleted_user = User.query.filter_by(username='testuser').first()
            assert deleted_user is None
            
            print("✓ User模型CRUD测试通过")
    
    def test_knowledge_item_model_crud(self, app):
        """MODEL-002: KnowledgeItem模型CRUD"""
        with app.app_context():
            # Create
            item = KnowledgeItem(
                title='测试标题',
                content='测试内容',
                source_url='http://example.com',
                source_name='测试来源',
                source_type='web',
                category='科技'
            )
            db.session.add(item)
            db.session.commit()
            
            # Read
            found_item = KnowledgeItem.query.filter_by(title='测试标题').first()
            assert found_item is not None
            assert found_item.content == '测试内容'
            assert found_item.category == '科技'
            
            # Update
            found_item.category = '教育'
            db.session.commit()
            updated_item = KnowledgeItem.query.filter_by(title='测试标题').first()
            assert updated_item.category == '教育'
            
            # Delete
            db.session.delete(updated_item)
            db.session.commit()
            deleted_item = KnowledgeItem.query.filter_by(title='测试标题').first()
            assert deleted_item is None
            
            print("✓ KnowledgeItem模型CRUD测试通过")
    
    def test_search_history_model_crud(self, app):
        """MODEL-003: SearchHistory模型CRUD"""
        with app.app_context():
            # 先创建一个用户
            user = User(username='testuser', email='test@example.com')
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()
            
            # Create
            history = SearchHistory(
                user_id=user.id,
                query='测试查询',
                query_type='semantic',
                results_count=5
            )
            db.session.add(history)
            db.session.commit()
            
            # Read
            found_history = db.session.query(SearchHistory).filter_by(user_id=user.id).first()
            assert found_history is not None
            assert found_history.query == '测试查询'
            assert found_history.query_type == 'semantic'
            assert found_history.results_count == 5
            
            # Update
            found_history.results_count = 10
            db.session.commit()
            updated_history = db.session.query(SearchHistory).filter_by(user_id=user.id).first()
            assert updated_history.results_count == 10
            
            # Delete
            db.session.delete(updated_history)
            db.session.delete(user)
            db.session.commit()
            
            print("✓ SearchHistory模型CRUD测试通过")
