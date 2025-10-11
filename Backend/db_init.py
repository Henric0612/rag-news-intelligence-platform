#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化模块 - 简化版本
"""
import os
from pathlib import Path


def cleanup_database_connections(db, verbose=False):
    """清理数据库连接 - 开发环境简化版本"""
    try:
        # 只清理引擎，不操作session（避免应用上下文问题）
        if hasattr(db, 'engine') and db.engine:
            db.engine.dispose()
            if verbose:
                print("   数据库引擎已清理")
        elif verbose:
            print("   无需清理数据库连接")
    except Exception as e:
        if verbose:
            print(f"   清理数据库引擎时出错: {e}")


def enable_wal_mode(db):
    """启用SQLite WAL模式"""
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            # 启用WAL模式
            result = conn.execute(text('PRAGMA journal_mode=WAL'))
            journal_mode = result.fetchone()[0]
            print(f"当前日志模式: {journal_mode}")
            
            # 设置其他优化参数
            conn.execute(text('PRAGMA synchronous=NORMAL'))
            conn.execute(text('PRAGMA cache_size=-32000'))
            conn.execute(text('PRAGMA foreign_keys=ON'))
            conn.execute(text('PRAGMA busy_timeout=10000'))
            conn.commit()
        
        print("WAL模式已启用")
        return True
    except Exception as e:
        print(f"启用WAL模式失败: {e}")
        return False


def ensure_database_directory(db_uri, verbose=False):
    """确保数据库目录存在"""
    if db_uri.startswith('sqlite:///'):
        db_path = Path(db_uri.replace('sqlite:///', ''))
        db_dir = db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        if verbose:
            print(f"   数据库目录: {db_dir}")
        return True
    return False
