"""
健康检查缓存服务
提供服务状态缓存、自动刷新和智能重连功能
"""

import time
import threading
from typing import Dict, Any, Optional
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class HealthCacheService:
    """健康检查缓存服务"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 30  # 缓存30秒
        self.refresh_interval = 10  # 每10秒检查一次
        self.auto_refresh = True
        self.refresh_thread = None
        self.stop_refresh = False
        
        # 启动自动刷新线程
        self._start_auto_refresh()
    
    def _start_auto_refresh(self):
        """启动自动刷新线程"""
        if self.refresh_thread is None or not self.refresh_thread.is_alive():
            self.stop_refresh = False
            self.refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
            self.refresh_thread.start()
            logger.info("健康检查自动刷新线程已启动")
    
    def _auto_refresh_worker(self):
        """自动刷新工作线程"""
        while not self.stop_refresh:
            try:
                if self.auto_refresh:
                    self._refresh_all_services()
                time.sleep(self.refresh_interval)
            except Exception as e:
                logger.error(f"自动刷新线程错误: {str(e)}")
                time.sleep(5)  # 出错时等待5秒再继续
    
    def _refresh_all_services(self):
        """刷新所有服务状态"""
        try:
            # 刷新LLM服务状态
            self._refresh_llm_service()
            
            # 刷新其他服务状态
            self._refresh_other_services()
            
        except Exception as e:
            logger.error(f"刷新服务状态失败: {str(e)}")
    
    def _refresh_llm_service(self):
        """刷新LLM服务状态"""
        try:
            from .llm_service import get_llm_service
            llm_service = get_llm_service()
            
            # 如果LLM服务不可用，尝试重连
            if not llm_service.is_initialized or llm_service.llm is None:
                logger.info("检测到LLM服务不可用，尝试自动重连...")
                if llm_service.ensure_connection():
                    logger.info("LLM服务自动重连成功")
                else:
                    logger.warning("LLM服务自动重连失败")
            
            # 更新缓存
            self.cache['llm_service'] = {
                'status': llm_service.health_check(deep_check=False),
                'timestamp': time.time(),
                'is_healthy': llm_service.is_initialized and llm_service.llm is not None
            }
            
        except Exception as e:
            logger.error(f"刷新LLM服务状态失败: {str(e)}")
    
    def _refresh_other_services(self):
        """刷新其他服务状态"""
        try:
            # 刷新向量服务
            from .vector_service import get_vector_service
            vector_service = get_vector_service()
            self.cache['vector_service'] = {
                'status': vector_service.health_check(deep_check=False),
                'timestamp': time.time(),
                'is_healthy': vector_service.embedding_model is not None
            }
            
            # 刷新搜索服务
            from .search_service import get_search_service
            search_service = get_search_service()
            self.cache['search_service'] = {
                'status': search_service.health_check(deep_check=False),
                'timestamp': time.time(),
                'is_healthy': True  # 搜索服务通常总是可用的
            }
            
        except Exception as e:
            logger.error(f"刷新其他服务状态失败: {str(e)}")
    
    def get_cached_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存的服务状态"""
        if service_name in self.cache:
            cached_data = self.cache[service_name]
            # 检查缓存是否过期
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['status']
            else:
                # 缓存过期，删除
                del self.cache[service_name]
        return None
    
    def get_llm_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """获取LLM服务状态"""
        if not force_refresh:
            cached_status = self.get_cached_status('llm_service')
            if cached_status:
                return cached_status
        
        # 强制刷新或缓存不可用
        try:
            from .llm_service import get_llm_service
            llm_service = get_llm_service()
            
            # 如果服务不可用，尝试重连
            if not llm_service.is_initialized or llm_service.llm is None:
                logger.info("LLM服务不可用，尝试重连...")
                llm_service.ensure_connection()
            
            status = llm_service.health_check(deep_check=False)
            
            # 更新缓存
            self.cache['llm_service'] = {
                'status': status,
                'timestamp': time.time(),
                'is_healthy': llm_service.is_initialized and llm_service.llm is not None
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取LLM服务状态失败: {str(e)}")
            return {'error': str(e)}
    
    def get_overall_status(self) -> Dict[str, Any]:
        """获取整体服务状态"""
        try:
            from .rag_service import get_rag_service
            rag_service = get_rag_service()
            
            # 执行健康检查，支持自动重连
            status = rag_service.health_check(deep_check=False)
            
            return {
                'overall_health': status.get('overall_health', False),
                'service_summary': status.get('service_summary', {}),
                'timestamp': time.time(),
                'auto_refresh_enabled': self.auto_refresh
            }
            
        except Exception as e:
            logger.error(f"获取整体服务状态失败: {str(e)}")
            return {'error': str(e)}
    
    def enable_auto_refresh(self, enabled: bool = True):
        """启用/禁用自动刷新"""
        self.auto_refresh = enabled
        if enabled:
            self._start_auto_refresh()
        logger.info(f"自动刷新已{'启用' if enabled else '禁用'}")
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.stop_refresh = True
        self.auto_refresh = False
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.refresh_thread.join(timeout=5)
        logger.info("自动刷新已停止")
    
    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()
        logger.info("健康检查缓存已清除")


# 全局健康缓存服务实例
health_cache_service = None


def get_health_cache_service() -> HealthCacheService:
    """获取健康缓存服务实例"""
    global health_cache_service
    if health_cache_service is None:
        health_cache_service = HealthCacheService()
    return health_cache_service
