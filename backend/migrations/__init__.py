#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 数据库迁移包
管理数据库结构的版本控制和迁移脚本
"""

__version__ = "1.0.0"
__description__ = "AI管理系统数据库迁移脚本"

# 迁移历史记录
MIGRATION_HISTORY = [
    {
        "version": "001",
        "name": "init_tables", 
        "description": "创建初始数据表结构",
        "created_at": "2024-01-01"
    }
    # 后续迁移将在这里添加
]

def get_migration_info():
    """获取迁移信息"""
    return {
        "package_version": __version__,
        "description": __description__,
        "migration_count": len(MIGRATION_HISTORY),
        "latest_migration": MIGRATION_HISTORY[-1] if MIGRATION_HISTORY else None
    }