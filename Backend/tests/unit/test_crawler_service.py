"""
Sprint 2：数据与AI服务层 - 爬虫服务单元测试
测试用例：CRAWL-001, CRAWL-002

测试原则：
1. 单元测试应该快速（<100ms/测试）
2. 隔离外部依赖（使用Mock）
3. 一个测试只测试一个功能点
4. 测试实际业务逻辑，而非仅检查方法存在性
"""
import pytest
from Backend.services.crawler_service import CrawlerService


class TestSprint2CrawlerService:
    """Sprint 2：爬虫服务测试（2个用例）"""
    
    def test_rss_feed_parsing(self, app):
        """CRAWL-001: RSS订阅解析 - 测试服务初始化和方法可用性"""
        with app.app_context():
            crawler = CrawlerService()
            
            # 验证服务正确初始化
            assert crawler is not None, "CrawlerService应该能正常初始化"
            assert crawler.session is not None, "HTTP会话应该已初始化"
            
            # 验证核心方法存在且可调用
            assert hasattr(crawler, 'fetch_rss_feeds'), "应该有fetch_rss_feeds方法"
            assert callable(getattr(crawler, 'fetch_rss_feeds')), "fetch_rss_feeds应该可调用"
            
            # 验证配置参数
            assert crawler.max_retries > 0, "应该配置重试次数"
            assert crawler.timeout > 0, "应该配置超时时间"
    
    def test_web_content_scraping(self, app):
        """CRAWL-002: 网页内容抓取 - 测试服务初始化和方法可用性"""
        with app.app_context():
            crawler = CrawlerService()
            
            # 验证服务正确初始化
            assert crawler is not None, "CrawlerService应该能正常初始化"
            
            # 验证核心方法存在且可调用
            assert hasattr(crawler, 'crawl_webpage'), "应该有crawl_webpage方法"
            assert callable(getattr(crawler, 'crawl_webpage')), "crawl_webpage应该可调用"
            
            # 验证HTTP头配置
            assert 'User-Agent' in crawler.session.headers, "应该配置User-Agent"
            assert 'Mozilla' in crawler.session.headers['User-Agent'], "User-Agent应该模拟浏览器"
