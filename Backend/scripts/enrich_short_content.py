# -*- coding: utf-8 -*-
"""
修复短内容条目脚本 - 为内容过短的RSS条目补充完整内容

使用场景：
1. 修复历史数据中内容过短的条目
2. 为已存在的摘要类内容获取完整正文
3. 提升知识库整体内容质量

运行方式：
    cd Backend
    python -m scripts.enrich_short_content
"""
import sys
import os
import logging
from datetime import datetime, timezone

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

from Backend.models import db, KnowledgeItem
from Backend.services.crawler_service import CrawlerService
from Backend.utils.content_quality import assess_content_quality
from Backend.app import create_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def enrich_short_content_items(
    min_length: int = 200,
    dry_run: bool = False,
    limit: int = None
):
    """
    为内容过短的条目补充完整内容
    
    Args:
        min_length: 最小内容长度阈值（字符）
        dry_run: 是否为演练模式（不实际修改数据）
        limit: 限制处理的条目数量
    """
    logger.info("=" * 80)
    logger.info("开始修复短内容条目")
    logger.info(f"配置: min_length={min_length}, dry_run={dry_run}, limit={limit}")
    logger.info("=" * 80)
    
    # 初始化爬虫服务
    crawler_service = CrawlerService()
    
    # 查询内容过短的RSS条目
    query = KnowledgeItem.query.filter(
        db.func.length(KnowledgeItem.content) < min_length,
        KnowledgeItem.source_url.isnot(None),
        KnowledgeItem.source_type == 'rss'
    ).order_by(KnowledgeItem.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    short_items = query.all()
    
    logger.info(f"找到 {len(short_items)} 个内容过短的条目")
    
    if not short_items:
        logger.info("没有需要处理的条目")
        return
    
    # 统计信息
    stats = {
        'total': len(short_items),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'improved_length': 0
    }
    
    # 处理每个条目
    for i, item in enumerate(short_items, 1):
        try:
            original_length = len(item.content)
            logger.info(f"\n[{i}/{stats['total']}] 处理条目 ID={item.id}")
            logger.info(f"  标题: {item.title[:50]}...")
            logger.info(f"  原内容长度: {original_length} 字符")
            logger.info(f"  来源: {item.source_url}")
            
            # 抓取完整内容
            full_content = crawler_service._fetch_full_text_from_url(item.source_url)
            
            if not full_content:
                logger.warning(f"  ✗ 无法获取完整内容")
                stats['failed'] += 1
                continue
            
            new_length = len(full_content)
            
            # 检查是否有改进
            if new_length <= original_length:
                logger.info(f"  → 新内容未改进({new_length}字 <= {original_length}字)，跳过")
                stats['skipped'] += 1
                continue
            
            improvement = new_length - original_length
            logger.info(f"  ✓ 获取到更好的内容: {new_length} 字符 (+{improvement})")
            
            if dry_run:
                logger.info(f"  [演练模式] 跳过实际更新")
                stats['success'] += 1
                stats['improved_length'] += improvement
                continue
            
            # 更新内容
            item.content = full_content
            
            # 重新评估质量
            try:
                quality_result = assess_content_quality(full_content, item.title)
                old_score = item.quality_score
                item.quality_score = quality_result['quality_score']
                logger.info(f"  质量评分: {old_score} → {item.quality_score}")
            except Exception as e:
                logger.warning(f"  质量评估失败: {str(e)}")
            
            # 标记需要重新向量化
            if item.vector_id:
                logger.info(f"  标记为需要重新向量化")
                # 可以选择清空vector_id，强制重新向量化
                # item.vector_id = None
                # item.status = 'pending'
            
            item.updated_at = datetime.now(timezone.utc)
            
            # 提交更改
            db.session.commit()
            
            logger.info(f"  ✓ 更新成功")
            stats['success'] += 1
            stats['improved_length'] += improvement
            
        except Exception as e:
            logger.error(f"  ✗ 处理失败: {str(e)}", exc_info=True)
            db.session.rollback()
            stats['failed'] += 1
            continue
    
    # 输出统计信息
    logger.info("\n" + "=" * 80)
    logger.info("处理完成 - 统计信息")
    logger.info("=" * 80)
    logger.info(f"总计: {stats['total']} 个条目")
    logger.info(f"成功: {stats['success']} 个")
    logger.info(f"失败: {stats['failed']} 个")
    logger.info(f"跳过: {stats['skipped']} 个")
    logger.info(f"总改进长度: {stats['improved_length']} 字符")
    if stats['success'] > 0:
        logger.info(f"平均改进: {stats['improved_length'] // stats['success']} 字符/条目")
    logger.info("=" * 80)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='修复短内容条目')
    parser.add_argument(
        '--min-length',
        type=int,
        default=200,
        help='最小内容长度阈值（默认: 200）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='演练模式，不实际修改数据'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='限制处理的条目数量'
    )
    
    args = parser.parse_args()
    
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        enrich_short_content_items(
            min_length=args.min_length,
            dry_run=args.dry_run,
            limit=args.limit
        )


if __name__ == '__main__':
    main()

