"""
爬虫服务 - 负责RSS订阅源解析和网页内容抓取
"""
import os
import re
import time
import logging
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from sqlalchemy.exc import SQLAlchemyError

from ..models import db, RSSSource, CrawlTask, KnowledgeItem
from ..services.knowledge_service import KnowledgeService
from ..services.vector_service import VectorService
from ..utils.text_utils import clean_text, extract_keywords
from ..utils.markdown_utils import html_to_markdown
from ..utils.content_quality import assess_content_quality

# 尝试导入 trafilatura，如果失败则使用备用方案
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logging.warning("trafilatura not available, falling back to BeautifulSoup extraction")

logger = logging.getLogger(__name__)


class CrawlerService:
    """爬虫服务类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self._knowledge_service = None
        self._vector_service = None
        
        # 爬取配置
        self.max_retries = 3
        self.timeout = 30
        self.delay_between_requests = 1  # 秒
    
    @property
    def knowledge_service(self):
        """懒加载知识库服务"""
        if self._knowledge_service is None:
            self._knowledge_service = KnowledgeService()
        return self._knowledge_service
    
    @property
    def vector_service(self):
        """懒加载向量服务（避免不必要的模型加载）"""
        if self._vector_service is None:
            self._vector_service = VectorService()
        return self._vector_service
        
    def fetch_rss_feeds(self, rss_sources: List[RSSSource] = None) -> Dict[str, any]:
        """
        抓取RSS订阅源
        
        Args:
            rss_sources: RSS源列表，如果为None则抓取所有活跃源
            
        Returns:
            Dict: 抓取结果统计
        """
        if rss_sources is None:
            rss_sources = RSSSource.query.filter_by(is_active=True).all()
        
        if not rss_sources:
            return {
                'success': True,
                'message': '没有活跃的RSS源需要抓取',
                'total_sources': 0,
                'total_items': 0,
                'successful_sources': 0,
                'failed_sources': 0
            }
        
        results = {
            'total_sources': len(rss_sources),
            'total_items': 0,
            'successful_sources': 0,
            'failed_sources': 0,
            'errors': []
        }
        
        for rss_source in rss_sources:
            try:
                # 创建爬取任务
                task = self._create_crawl_task(rss_source, 'rss')
                
                # 执行RSS抓取
                items = self._fetch_rss_feed(rss_source)
                
                if items:
                    # 保存抓取到的内容
                    saved_count = self._save_crawled_content(items, rss_source)
                    task.status = 'completed'
                    task.items_crawled = saved_count
                    task.completed_at = datetime.now(timezone.utc)
                    
                    results['total_items'] += saved_count
                    results['successful_sources'] += 1
                    
                    # 更新RSS源的最后抓取时间
                    rss_source.last_crawled = datetime.now(timezone.utc)
                else:
                    task.status = 'failed'
                    task.error_message = '没有抓取到任何内容'
                    results['failed_sources'] += 1
                    results['errors'].append(f"RSS源 {rss_source.name} 没有抓取到内容")
                
                db.session.commit()
                logger.info(f"RSS源 {rss_source.name} 抓取完成，获得 {task.items_crawled} 条内容")
                
                # 请求间隔
                time.sleep(self.delay_between_requests)
                
            except Exception as e:
                logger.error(f"RSS源 {rss_source.name} 抓取失败: {str(e)}")
                results['failed_sources'] += 1
                results['errors'].append(f"RSS源 {rss_source.name} 抓取失败: {str(e)}")
                
                if 'task' in locals():
                    task.status = 'failed'
                    task.error_message = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
        
        results['success'] = results['failed_sources'] == 0
        results['message'] = f"抓取完成: {results['successful_sources']} 个源成功，{results['failed_sources']} 个源失败"
        
        return results
    
    def _fetch_rss_feed(self, rss_source: RSSSource) -> List[Dict]:
        """
        抓取单个RSS订阅源
        
        Args:
            rss_source: RSS源对象
            
        Returns:
            List[Dict]: 抓取到的内容列表
        """
        items = []
        
        try:
            logger.info(f"开始抓取RSS源: {rss_source.url}")
            
            # 先使用带UA的会话请求，再由 feedparser 解析内容，避免部分源对默认UA屏蔽
            response = self.session.get(rss_source.url, timeout=self.timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"RSS源 {rss_source.url} 解析有警告: {feed.bozo_exception}")
            
            if not getattr(feed, 'entries', None):
                logger.warning(f"RSS源 {rss_source.url} 没有找到条目")
                return items
            
            # 处理每个条目
            for entry in feed.entries:
                try:
                    # 提取基本信息
                    title = self._extract_title(entry)
                    content = self._extract_content(entry)
                    link = self._extract_link(entry)
                    published = self._extract_published_date(entry)
                    
                    if not title or not content:
                        continue
                    
                    # 转换为Markdown
                    try:
                        # RSS内容通常包含HTML
                        from ..utils.markdown_utils import content_to_markdown
                        markdown_content = content_to_markdown(content, link or rss_source.url)
                    except Exception as e:
                        logger.warning(f"RSS条目Markdown转换失败: {str(e)}")
                        markdown_content = None
                    
                    # 构建内容项
                    item = {
                        'title': title,
                        'content': content,
                        'markdown_content': markdown_content,
                        'source_url': link or rss_source.url,
                        'source_name': rss_source.name,
                        'source_type': 'rss',
                        'category': rss_source.category,
                        'published_at': published,
                        'tags': self._extract_tags(entry, rss_source.category)
                    }
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.error(f"处理RSS条目失败: {str(e)}")
                    continue
            
            logger.info(f"RSS源 {rss_source.url} 抓取到 {len(items)} 条内容")
            
        except Exception as e:
            logger.error(f"抓取RSS源 {rss_source.url} 失败: {str(e)}")
            raise
        
        return items
    
    def crawl_webpage(self, url: str, category: str = None) -> Dict:
        """
        抓取单个网页内容
        
        Args:
            url: 网页URL
            category: 内容分类
            
        Returns:
            Dict: 抓取结果
        """
        try:
            logger.info(f"开始抓取网页: {url}")
            
            # 创建临时RSS源用于任务记录
            temp_source = RSSSource(
                name=f"Web Crawl: {urlparse(url).netloc}",
                url=url,
                category=category or 'web'
            )
            
            # 创建爬取任务
            try:
                task = self._create_crawl_task(temp_source, 'web')
                logger.info(f"爬取任务创建成功: task_id={task.id}, source_id={task.source_id}")
            except Exception as task_error:
                logger.error(f"创建爬取任务失败: {str(task_error)}", exc_info=True)
                raise
            
            # 抓取网页内容
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析HTML内容
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取内容
            title = self._extract_webpage_title(soup)
            content = self._extract_webpage_content(soup)
            
            if not title or not content:
                task.status = 'failed'
                task.error_message = '无法提取网页标题或内容'
                task.completed_at = datetime.now(timezone.utc)
                db.session.commit()
                
                return {
                    'success': False,
                    'message': '无法提取网页标题或内容',
                    'url': url
                }
            
            # 转换为Markdown
            try:
                markdown_content = html_to_markdown(str(soup), url)
            except Exception as e:
                logger.warning(f"Markdown转换失败: {str(e)}")
                markdown_content = None
            
            # 构建内容项
            item = {
                'title': title,
                'content': content,
                'markdown_content': markdown_content,
                'source_url': url,
                'source_name': urlparse(url).netloc,
                'source_type': 'web',
                'category': category or 'web',
                'published_at': datetime.now(timezone.utc),
                'tags': self._extract_webpage_tags(soup, category)
            }
            
            # 保存内容
            saved_count = self._save_crawled_content([item], temp_source)
            
            task.status = 'completed'
            task.items_crawled = saved_count
            task.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'成功抓取网页内容，保存了 {saved_count} 条记录',
                'url': url,
                'title': title,
                'content_length': len(content)
            }
            
        except Exception as e:
            logger.error(f"抓取网页 {url} 失败: {str(e)}")
            
            if 'task' in locals():
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = datetime.now(timezone.utc)
                db.session.commit()
            
            return {
                'success': False,
                'message': f'抓取失败: {str(e)}',
                'url': url
            }
    
    def _create_crawl_task(self, rss_source: RSSSource, task_type: str) -> CrawlTask:
        """创建爬取任务记录"""
        task = CrawlTask(
            source_id=rss_source.id if rss_source.id else None,
            task_type=task_type,
            status='running',
            started_at=datetime.now(timezone.utc)
        )
        
        db.session.add(task)
        db.session.flush()  # 获取task.id
        
        return task
    
    def _save_crawled_content(self, items: List[Dict], rss_source: RSSSource) -> int:
        """
        保存抓取到的内容到知识库
        
        Args:
            items: 内容项列表
            rss_source: RSS源对象
            
        Returns:
            int: 成功保存的数量
        """
        saved_count = 0
        
        for item in items:
            try:
                # 检查是否已存在（基于URL和内容hash）
                existing_item = KnowledgeItem.query.filter(
                    db.or_(
                        KnowledgeItem.source_url == item['source_url'],
                        KnowledgeItem.content_hash == self._generate_content_hash(item['content'])
                    )
                ).first()
                
                if existing_item:
                    logger.debug(f"内容已存在，跳过: {item['title']}")
                    continue
                
                # 评估内容质量
                quality_result = assess_content_quality(item['content'], item['title'])
                quality_score = quality_result['quality_score']
                
                # 创建知识库条目
                knowledge_item = KnowledgeItem(
                    title=item['title'],
                    content=item['content'],
                    source_url=item['source_url'],
                    source_name=item['source_name'],
                    source_type=item['source_type'],
                    category=item['category'],
                    tags=item.get('tags', []),
                    content_hash=self._generate_content_hash(item['content']),
                    quality_score=quality_score,
                    published_at=item.get('published_at'),
                    created_at=datetime.now(timezone.utc)
                )
                
                db.session.add(knowledge_item)
                db.session.flush()  # 获取knowledge_item.id
                
                # 向量化并保存到FAISS
                try:
                    vector_id = self.vector_service.add_document(
                        knowledge_item.id,
                        item['title'] + ' ' + item['content']
                    )
                    knowledge_item.vector_id = vector_id
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"向量化失败: {str(e)}")
                    # 即使向量化失败，也保存文本内容
                    saved_count += 1
                
            except SQLAlchemyError as e:
                logger.error(f"保存知识库条目失败: {str(e)}")
                db.session.rollback()
                continue
            except Exception as e:
                logger.error(f"处理内容项失败: {str(e)}")
                continue
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"提交数据库事务失败: {str(e)}")
            db.session.rollback()
        
        return saved_count
    
    def _extract_title(self, entry) -> str:
        """提取RSS条目标题"""
        title = getattr(entry, 'title', '')
        return clean_text(title) if title else ''
    
    def _extract_content(self, entry) -> str:
        """提取RSS条目内容"""
        content = ''
        
        # 尝试不同的内容字段
        for field in ['content', 'summary', 'description']:
            if hasattr(entry, field):
                field_value = entry[field]
                if isinstance(field_value, list) and field_value:
                    content = field_value[0].get('value', '')
                elif isinstance(field_value, str):
                    content = field_value
                
                if content:
                    break
        
        # 使用 trafilatura 提取高质量文本
        if content and TRAFILATURA_AVAILABLE:
            try:
                # trafilatura 专门用于提取网页正文
                extracted_text = trafilatura.extract(content)
                if extracted_text and len(extracted_text.strip()) > 50:
                    content = clean_text(extracted_text)
                    logger.debug(f"使用 trafilatura 成功提取内容，长度: {len(content)}")
                else:
                    # trafilatura 提取失败，降级到 BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text()
                    content = clean_text(content)
                    logger.debug(f"trafilatura 提取失败，使用 BeautifulSoup，长度: {len(content)}")
            except Exception as e:
                logger.warning(f"trafilatura 提取失败: {str(e)}，使用 BeautifulSoup")
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text()
                content = clean_text(content)
        elif content:
            # 使用 BeautifulSoup 作为备用方案
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
            content = clean_text(content)
        
        return content
    
    def _extract_link(self, entry) -> str:
        """提取RSS条目链接"""
        return getattr(entry, 'link', '')
    
    def _extract_published_date(self, entry) -> datetime:
        """提取RSS条目发布日期"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception:
            pass
        
        return datetime.now(timezone.utc)
    
    def _extract_tags(self, entry, category: str = None) -> List[str]:
        """提取RSS条目标签"""
        tags = []
        
        # 从category字段提取标签
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    tags.append(tag.term)
        
        # 添加分类作为标签
        if category:
            tags.append(category)
        
        # 从内容中提取关键词
        if hasattr(entry, 'title'):
            keywords = extract_keywords(entry.title)
            tags.extend(keywords[:3])  # 最多添加3个关键词
        
        return list(set(tags))  # 去重
    
    def _extract_webpage_title(self, soup: BeautifulSoup) -> str:
        """提取网页标题"""
        title = ''
        
        # 尝试不同的标题选择器
        title_selectors = ['title', 'h1', '.title', '.headline', '.article-title']
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title:
                    break
        
        return clean_text(title) if title else ''
    
    def _extract_webpage_content(self, soup: BeautifulSoup) -> str:
        """提取网页正文内容"""
        # 优先使用 trafilatura 提取
        if TRAFILATURA_AVAILABLE:
            try:
                # 将 BeautifulSoup 对象转换为 HTML 字符串
                html_content = str(soup)
                extracted_text = trafilatura.extract(html_content)
                if extracted_text and len(extracted_text.strip()) > 50:
                    content = clean_text(extracted_text)
                    logger.debug(f"使用 trafilatura 成功提取网页内容，长度: {len(content)}")
                    return content
            except Exception as e:
                logger.warning(f"trafilatura 网页提取失败: {str(e)}，使用 BeautifulSoup")
        
        # 备用方案：使用 BeautifulSoup
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            tag.decompose()
        
        # 尝试找到主要内容区域
        content_selectors = [
            'article',
            '.article-content',
            '.content',
            '.main-content',
            '.post-content',
            '.entry-content',
            'main',
            '.container'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        if not content_element:
            content_element = soup.body
        
        if content_element:
            content = content_element.get_text()
            content = clean_text(content)
            
            # 如果内容太短，可能不是正文
            if len(content) < 100:
                # 尝试提取所有段落
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs])
                content = clean_text(content)
            
            return content
        
        return ''
    
    def _extract_webpage_tags(self, soup: BeautifulSoup, category: str = None) -> List[str]:
        """提取网页标签"""
        tags = []
        
        # 从meta标签提取关键词
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = meta_keywords['content'].split(',')
            tags.extend([kw.strip() for kw in keywords[:5]])
        
        # 从标题提取关键词
        title = soup.find('title')
        if title:
            keywords = extract_keywords(title.get_text())
            tags.extend(keywords[:3])
        
        # 添加分类
        if category:
            tags.append(category)
        
        return list(set(tags))
    
    def _generate_content_hash(self, content: str) -> str:
        """生成内容哈希值"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_crawl_statistics(self) -> Dict:
        """获取爬取统计信息"""
        try:
            # RSS源统计
            total_sources = RSSSource.query.count()
            active_sources = RSSSource.query.filter_by(is_active=True).count()
            
            # 爬取任务统计
            total_tasks = CrawlTask.query.count()
            completed_tasks = CrawlTask.query.filter_by(status='completed').count()
            failed_tasks = CrawlTask.query.filter_by(status='failed').count()
            
            # 最近24小时的爬取统计
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            recent_tasks = CrawlTask.query.filter(CrawlTask.created_at >= yesterday).count()
            
            # 知识库统计
            total_knowledge_items = KnowledgeItem.query.count()
            rss_items = KnowledgeItem.query.filter_by(source_type='rss').count()
            web_items = KnowledgeItem.query.filter_by(source_type='web').count()
            
            return {
                'rss_sources': {
                    'total': total_sources,
                    'active': active_sources,
                    'inactive': total_sources - active_sources
                },
                'crawl_tasks': {
                    'total': total_tasks,
                    'completed': completed_tasks,
                    'failed': failed_tasks,
                    'recent_24h': recent_tasks
                },
                'knowledge_items': {
                    'total': total_knowledge_items,
                    'rss': rss_items,
                    'web': web_items
                }
            }
            
        except Exception as e:
            logger.error(f"获取爬取统计信息失败: {str(e)}")
            return {
                'error': str(e)
            }
    
    def schedule_crawling_tasks(self):
        """调度爬取任务（定时任务入口）"""
        try:
            logger.info("开始执行定时爬取任务")
            
            # 获取需要爬取的RSS源（超过爬取频率的源）
            now = datetime.now(timezone.utc)
            sources_to_crawl = []
            
            for source in RSSSource.query.filter_by(is_active=True).all():
                if not source.last_crawled:
                    # 从未爬取过
                    sources_to_crawl.append(source)
                else:
                    # 检查是否超过爬取频率
                    time_since_last_crawl = now - source.last_crawled
                    if time_since_last_crawl.total_seconds() >= source.crawl_frequency:
                        sources_to_crawl.append(source)
            
            if sources_to_crawl:
                result = self.fetch_rss_feeds(sources_to_crawl)
                logger.info(f"定时爬取任务完成: {result['message']}")
                return result
            else:
                logger.info("没有需要爬取的RSS源")
                return {
                    'success': True,
                    'message': '没有需要爬取的RSS源',
                    'total_sources': 0
                }
                
        except Exception as e:
            logger.error(f"定时爬取任务失败: {str(e)}")
            return {
                'success': False,
                'message': f'定时爬取任务失败: {str(e)}'
            }
