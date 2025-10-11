"""
Sprint 2：数据与AI服务层 - 知识库服务单元测试
测试用例：KNOW-001, KNOW-002, KNOW-003
"""
import pytest
from Backend.services.knowledge_service import KnowledgeService
from Backend.models.knowledge import KnowledgeItem
from Backend.models import db


class TestSprint2KnowledgeService:
    """Sprint 2：知识库服务测试（3个用例）"""
    
    def test_create_knowledge_item(self, app):
        """KNOW-001: 创建知识库条目"""
        with app.app_context():
            item = KnowledgeService.create_knowledge_item(
                title='测试标题',
                content='测试内容',
                source_url='https://example.com',
                source_type='web',
                category='测试分类',
                tags=['测试', '示例']
            )
            
            assert item is not None
            assert item.title == '测试标题'
            assert item.content == '测试内容'
            assert item.source_type == 'web'
    
    def test_get_knowledge_items_paginated(self, app):
        """KNOW-002: 获取知识库列表"""
        with app.app_context():
            # 创建多个测试条目
            for i in range(5):
                KnowledgeService.create_knowledge_item(
                    title=f'测试标题{i}',
                    content=f'测试内容{i}',
                    source_url=f'https://example.com/{i}',
                    source_type='web',
                    category='测试分类',
                    tags=['测试']
                )
            
            # 测试分页
            result = KnowledgeService.get_knowledge_items(page=1, per_page=3)
            
            assert result['items'] is not None
            assert len(result['items']) == 3
            assert result['total'] == 5
            assert result['page'] == 1
            assert result['pages'] == 2
    
    def test_update_knowledge_item(self, app):
        """KNOW-003: 更新知识库条目"""
        with app.app_context():
            # 先创建条目
            item = KnowledgeService.create_knowledge_item(
                title='原始标题',
                content='原始内容',
                source_url='https://example.com',
                source_type='web',
                category='测试分类',
                tags=['测试']
            )
            
            # 更新条目
            updated_item = KnowledgeService.update_knowledge_item(
                item.id, 
                title='更新标题',
                content='更新内容'
            )
            
            assert updated_item.title == '更新标题'
            assert updated_item.content == '更新内容'
    
    def test_delete_knowledge_item(self, app):
        """KNOW-004: 删除知识库条目"""
        with app.app_context():
            # 先创建条目
            item = KnowledgeService.create_knowledge_item(
                title='测试标题',
                content='测试内容',
                source_url='https://example.com',
                source_type='web',
                category='测试分类',
                tags=['测试']
            )
            item_id = item.id
            
            # 删除条目
            success = KnowledgeService.delete_knowledge_item(item_id)
            assert success is True
            
            # 验证条目已被删除
            deleted_item = db.session.get(KnowledgeItem, item_id)
            assert deleted_item is None
    
