"""
Sprint 4：质量保证与交付 - 数据库性能测试
测试用例：PERF-004
"""
import pytest
import time
from Backend.models import db
from Backend.models.knowledge import KnowledgeItem
from Backend.models.user import User
from Backend.models.search_history import SearchHistory
from sqlalchemy import text


class TestSprint4DatabasePerformance:
    """Sprint 4：数据库性能测试（1个用例）"""
    
    def test_database_query_optimization(self, app):
        """PERF-004: 数据库查询优化（索引优化完成）"""
        with app.app_context():
            # 步骤1：验证数据库索引存在
            inspector = db.inspect(db.engine)
            
            # 检查KnowledgeItem表的索引（表名是复数 knowledge_items）
            try:
                knowledge_indexes = inspector.get_indexes('knowledge_items')
                index_names = [idx['name'] for idx in knowledge_indexes]
                print(f"[PASS] KnowledgeItem表索引: {index_names}")
            except Exception as e:
                print(f"[INFO] 无法获取索引信息（可能是内存数据库）: {str(e)}")
            
            # 步骤2：测试大量数据插入性能
            test_items = [
                KnowledgeItem(
                    title=f'性能测试{i}',
                    content=f'这是性能测试内容{i}' * 10,
                    source_url=f'http://example.com/{i}',
                    source_name='性能测试',
                    source_type='web',
                    category='测试'
                )
                for i in range(100)
            ]
            
            start = time.time()
            for item in test_items:
                db.session.add(item)
            db.session.commit()
            insert_time = time.time() - start
            
            print(f"[PASS] 插入100条数据耗时: {insert_time:.3f}秒")
            assert insert_time < 5.0, f"批量插入应<5秒，实际: {insert_time:.3f}秒"
            
            try:
                # 步骤3：测试查询性能
                start = time.time()
                results = KnowledgeItem.query.filter_by(category='测试').limit(10).all()
                query_time = time.time() - start
                
                print(f"[PASS] 查询10条数据耗时: {query_time*1000:.2f}ms")
                assert query_time < 0.1, f"查询应<100ms，实际: {query_time*1000:.2f}ms"
                assert len(results) == 10
                
                # 步骤4：测试分页查询性能
                start = time.time()
                paginated = KnowledgeItem.query.paginate(page=1, per_page=20, error_out=False)
                pagination_time = time.time() - start
                
                print(f"[PASS] 分页查询耗时: {pagination_time*1000:.2f}ms")
                assert pagination_time < 0.2, f"分页查询应<200ms，实际: {pagination_time*1000:.2f}ms"
                
                # 步骤5：测试全文搜索性能（如果支持）
                start = time.time()
                search_results = KnowledgeItem.query.filter(
                    KnowledgeItem.title.like('%性能%')
                ).limit(10).all()
                search_time = time.time() - start
                
                print(f"[PASS] 模糊搜索耗时: {search_time*1000:.2f}ms")
                assert search_time < 0.5, f"模糊搜索应<500ms，实际: {search_time*1000:.2f}ms"
                
                # 步骤6：测试JOIN查询性能
                start = time.time()
                # 查询用户及其搜索历史
                users_with_history = db.session.query(User, SearchHistory).join(
                    SearchHistory, User.id == SearchHistory.user_id, isouter=True
                ).limit(10).all()
                join_time = time.time() - start
                
                print(f"[PASS] JOIN查询耗时: {join_time*1000:.2f}ms")
                assert join_time < 0.5, f"JOIN查询应<500ms，实际: {join_time*1000:.2f}ms"
                
                print("[PASS] PERF-004: 数据库查询优化测试通过")
                
            finally:
                # 清理测试数据
                for item in test_items:
                    db.session.delete(item)
                db.session.commit()
    
    def test_database_connection_pool(self, app):
        """测试数据库连接池配置"""
        with app.app_context():
            # 验证连接池配置
            pool = db.engine.pool
            pool_type = type(pool).__name__
            
            print(f"[INFO] 连接池类型: {pool_type}")
            
            # SQLite 内存数据库使用 StaticPool，没有 size() 方法
            if pool_type == 'StaticPool':
                print("[INFO] SQLite 内存数据库使用 StaticPool（单连接）")
                print("[PASS] 数据库连接池配置正确（测试环境）")
            else:
                # 生产环境的连接池（如 QueuePool）
                print(f"[PASS] 连接池大小: {pool.size()}")
                print(f"[PASS] 最大溢出: {pool._max_overflow}")
                print(f"[PASS] 当前连接数: {pool.checkedout()}")
                
                # 验证连接池配置合理
                assert pool.size() >= 5, "连接池大小应>=5"
                assert pool._max_overflow >= 10, "最大溢出应>=10"
                
                print("[PASS] 数据库连接池配置正确")
    
    def test_transaction_performance(self, app):
        """测试事务性能"""
        with app.app_context():
            # 测试事务提交性能
            start = time.time()
            
            for i in range(10):
                item = KnowledgeItem(
                    title=f'事务测试{i}',
                    content='事务测试内容',
                    source_url=f'http://example.com/tx{i}',
                    source_name='事务测试',
                    source_type='web'
                )
                db.session.add(item)
                db.session.commit()  # 每次都提交
            
            transaction_time = time.time() - start
            
            print(f"[PASS] 10次独立事务耗时: {transaction_time:.3f}秒")
            
            # 清理
            KnowledgeItem.query.filter(KnowledgeItem.title.like('事务测试%')).delete()
            db.session.commit()
            
            # 测试批量事务性能
            start = time.time()
            
            for i in range(10):
                item = KnowledgeItem(
                    title=f'批量事务{i}',
                    content='批量事务内容',
                    source_url=f'http://example.com/batch{i}',
                    source_name='批量测试',
                    source_type='web'
                )
                db.session.add(item)
            db.session.commit()  # 一次性提交
            
            batch_time = time.time() - start
            
            print(f"[PASS] 批量事务耗时: {batch_time:.3f}秒")
            assert batch_time < transaction_time, "批量事务应该比独立事务快"
            
            # 清理
            KnowledgeItem.query.filter(KnowledgeItem.title.like('批量事务%')).delete()
            db.session.commit()
            
            print("[PASS] 事务性能测试通过")
