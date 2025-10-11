"""
为现有知识库条目生成Markdown内容（独立脚本）
"""
import os
import sqlite3
import sys

# 添加项目根目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from utils.markdown_utils import content_to_markdown
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_existing_data():
    """为现有数据生成Markdown内容"""
    # 获取数据库路径
    db_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'data', 
        'sqlite', 
        'knowledge.db'
    )
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return
    
    logger.info(f"连接数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询需要迁移的数据（处理所有RSS和Web来源的，强制重新转换）
        cursor.execute("""
            SELECT id, content, source_url 
            FROM knowledge_items 
            WHERE source_type IN ('rss', 'web')
        """)
        
        items = cursor.fetchall()
        total = len(items)
        logger.info(f"找到 {total} 条需要迁移的记录")
        
        if total == 0:
            logger.info("没有需要迁移的数据")
            conn.close()
            return
        
        count = 0
        success = 0
        failed = 0
        
        for item_id, content, source_url in items:
            try:
                # 转换为Markdown
                markdown_content = content_to_markdown(content, source_url)
                
                if markdown_content:
                    # 更新数据库
                    cursor.execute(
                        "UPDATE knowledge_items SET markdown_content = ? WHERE id = ?",
                        (markdown_content, item_id)
                    )
                    success += 1
                else:
                    logger.warning(f"ID={item_id} 转换结果为空")
                    failed += 1
                
                count += 1
                
                # 每100条提交一次
                if count % 100 == 0:
                    conn.commit()
                    logger.info(f"进度: {count}/{total} ({count*100//total}%)")
                    
            except Exception as e:
                logger.error(f"处理失败 ID={item_id}: {str(e)}")
                failed += 1
        
        # 最后提交
        conn.commit()
        conn.close()
        
        logger.info("=" * 50)
        logger.info(f"迁移完成！")
        logger.info(f"总计: {total} 条")
        logger.info(f"成功: {success} 条")
        logger.info(f"失败: {failed} 条")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        raise


if __name__ == '__main__':
    migrate_existing_data()

