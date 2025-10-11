"""
更新所有知识库条目的质量评分

这个脚本会重新计算所有知识库条目的质量评分
适用于以下场景：
1. 质量评估算法更新后需要重新评估
2. 历史数据没有质量评分
3. 质量评分异常需要修复
"""
import sys
import os

# 添加项目根目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
project_dir = os.path.dirname(backend_dir)
sys.path.insert(0, project_dir)

from Backend.app import create_app
from Backend.models import db, KnowledgeItem
from Backend.utils.content_quality import assess_content_quality
from sqlalchemy import func
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_quality_scores():
    """更新所有知识库条目的质量评分"""
    app = create_app()
    
    with app.app_context():
        # 统计信息
        total_items = KnowledgeItem.query.count()
        logger.info(f"开始更新质量评分，共 {total_items} 条记录")
        
        if total_items == 0:
            logger.warning("知识库中没有数据")
            return
        
        # 统计当前评分分布
        zero_score_count = KnowledgeItem.query.filter(
            (KnowledgeItem.quality_score == 0) | (KnowledgeItem.quality_score.is_(None))
        ).count()
        logger.info(f"其中 {zero_score_count} 条记录评分为0或NULL")
        
        # 批量处理
        updated_count = 0
        error_count = 0
        score_stats = {
            'excellent': 0,  # >= 80
            'good': 0,       # >= 60
            'fair': 0,       # >= 40
            'poor': 0        # < 40
        }
        
        # 分批处理，避免一次性加载所有数据
        batch_size = 100
        offset = 0
        
        while offset < total_items:
            items = KnowledgeItem.query.offset(offset).limit(batch_size).all()
            
            for item in items:
                try:
                    # 重新评估内容质量
                    quality_result = assess_content_quality(item.content, item.title)
                    new_score = quality_result['quality_score']
                    old_score = item.quality_score or 0
                    
                    # 更新评分
                    item.quality_score = new_score
                    
                    # 统计等级分布
                    if new_score >= 80:
                        score_stats['excellent'] += 1
                    elif new_score >= 60:
                        score_stats['good'] += 1
                    elif new_score >= 40:
                        score_stats['fair'] += 1
                    else:
                        score_stats['poor'] += 1
                    
                    updated_count += 1
                    
                    if updated_count % 10 == 0:
                        logger.info(f"已处理 {updated_count}/{total_items} 条记录")
                    
                    # 记录评分变化较大的条目
                    if abs(new_score - old_score) > 10:
                        logger.debug(f"ID {item.id} 评分变化: {old_score:.1f} -> {new_score:.1f}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理ID {item.id} 时出错: {str(e)}")
                    continue
            
            # 提交当前批次
            try:
                db.session.commit()
                logger.info(f"批次提交成功: {offset}-{offset+batch_size}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"批次提交失败: {str(e)}")
            
            offset += batch_size
        
        # 输出统计结果
        logger.info("=" * 60)
        logger.info("质量评分更新完成！")
        logger.info(f"总记录数: {total_items}")
        logger.info(f"成功更新: {updated_count}")
        logger.info(f"失败记录: {error_count}")
        logger.info("-" * 60)
        logger.info("质量等级分布:")
        logger.info(f"  优秀 (≥80分): {score_stats['excellent']} ({score_stats['excellent']/total_items*100:.1f}%)")
        logger.info(f"  良好 (≥60分): {score_stats['good']} ({score_stats['good']/total_items*100:.1f}%)")
        logger.info(f"  一般 (≥40分): {score_stats['fair']} ({score_stats['fair']/total_items*100:.1f}%)")
        logger.info(f"  较差 (<40分): {score_stats['poor']} ({score_stats['poor']/total_items*100:.1f}%)")
        logger.info("=" * 60)
        
        # 显示一些示例
        logger.info("\n示例记录（前5条）:")
        sample_items = KnowledgeItem.query.order_by(KnowledgeItem.quality_score.desc()).limit(5).all()
        for item in sample_items:
            logger.info(f"  [{item.quality_score:.1f}分] {item.title[:50]}")


if __name__ == '__main__':
    try:
        update_quality_scores()
    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)

