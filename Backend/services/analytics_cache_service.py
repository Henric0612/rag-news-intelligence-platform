"""
Analytics Cache Service
Intelligent file-based caching for analytics reports
Only updates when knowledge base content changes
"""
import json
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class AnalyticsCacheService:
    """Analytics report caching service"""
    
    CACHE_DIR = Path(__file__).parent.parent / 'data' / 'cache'
    CACHE_FILE = CACHE_DIR / 'analytics_report.json'
    
    @classmethod
    def _ensure_cache_dir(cls):
        """Ensure cache directory exists"""
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_cache_key(cls) -> str:
        """
        Generate cache key based on knowledge base state
        Key format: count:latest_update_timestamp
        """
        from Backend.models import KnowledgeItem
        
        try:
            # Get latest updated item
            latest_item = KnowledgeItem.query.order_by(
                KnowledgeItem.updated_at.desc()
            ).first()
            
            # Get total count
            count = KnowledgeItem.query.count()
            
            if not latest_item:
                return f"kb:{count}:empty"
            
            # Use timestamp as part of key
            timestamp = latest_item.updated_at.timestamp() if latest_item.updated_at else 0
            return f"kb:{count}:{int(timestamp)}"
            
        except Exception as e:
            logger.error(f"Failed to generate cache key: {e}")
            return f"kb:error:{datetime.now(timezone.utc).timestamp()}"
    
    @classmethod
    def get_cached_report(cls) -> Optional[Dict[str, Any]]:
        """
        Get cached analytics report if valid
        Returns None if cache invalid or doesn't exist
        """
        try:
            if not cls.CACHE_FILE.exists():
                logger.info("No cache file found")
                return None
            
            # Read cache file
            with open(cls.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Validate cache structure
            if not isinstance(cache_data, dict) or 'cache_key' not in cache_data or 'report' not in cache_data:
                logger.warning("Invalid cache structure")
                return None
            
            # Check if cache is still valid (knowledge base not changed)
            current_key = cls.get_cache_key()
            cached_key = cache_data.get('cache_key')
            
            if current_key == cached_key:
                logger.info(f"✅ Cache hit! Key: {current_key}")
                return cache_data['report']
            else:
                logger.info(f"❌ Cache miss. Current: {current_key}, Cached: {cached_key}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode cache JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read cache: {e}")
            return None
    
    @classmethod
    def set_cached_report(cls, report: Dict[str, Any]) -> bool:
        """
        Cache analytics report with current knowledge base state
        Returns True if successful
        """
        try:
            cls._ensure_cache_dir()
            
            cache_key = cls.get_cache_key()
            cache_data = {
                'cache_key': cache_key,
                'report': report,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'cache_version': '1.0'
            }
            
            # Write to temp file first, then rename (atomic operation)
            temp_file = cls.CACHE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # Atomic rename
            temp_file.replace(cls.CACHE_FILE)
            
            logger.info(f"✅ Analytics report cached successfully. Key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache report: {e}")
            return False
    
    @classmethod
    def clear_cache(cls) -> bool:
        """
        Clear cached analytics report
        Returns True if successful
        """
        try:
            if cls.CACHE_FILE.exists():
                cls.CACHE_FILE.unlink()
                logger.info("✅ Cache cleared successfully")
                return True
            else:
                logger.info("No cache to clear")
                return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        """
        Get cache information for debugging
        """
        try:
            if not cls.CACHE_FILE.exists():
                return {
                    'exists': False,
                    'current_key': cls.get_cache_key()
                }
            
            with open(cls.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            return {
                'exists': True,
                'cached_key': cache_data.get('cache_key'),
                'current_key': cls.get_cache_key(),
                'cached_at': cache_data.get('cached_at'),
                'is_valid': cache_data.get('cache_key') == cls.get_cache_key(),
                'file_size': cls.CACHE_FILE.stat().st_size
            }
        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }

