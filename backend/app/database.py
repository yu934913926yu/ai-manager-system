#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 数据库连接管理
支持SQLite(开发)和MySQL(生产)无缝切换
"""

import os
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import asyncio

# 获取配置
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings

settings = get_settings()

# 🔧 数据库配置
DATABASE_URL = settings.DATABASE_URL
ASYNC_DATABASE_URL = DATABASE_URL

# 转换为异步URL (如果需要)
if settings.is_mysql:
    # MySQL异步驱动
    ASYNC_DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://")
elif settings.is_sqlite:
    # SQLite异步驱动
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

# 📊 创建数据库引擎
# 同步引擎 (用于初始化和迁移)
engine = create_engine(
    DATABASE_URL,
    **settings.get_database_config()
)

# 异步引擎 (用于API操作)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# 📝 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 🏗️ 数据库基类
Base = declarative_base()
metadata = MetaData()

# 🔄 数据库依赖注入
def get_db() -> Generator[Session, None, None]:
    """
    同步数据库会话依赖
    用于非异步操作
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    异步数据库会话依赖
    用于FastAPI路由
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@contextmanager
def get_db_context():
    """
    数据库上下文管理器
    用于事务操作
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# 🚀 数据库初始化函数
def create_database():
    """
    创建数据库 (仅MySQL需要)
    SQLite会自动创建文件
    """
    if settings.is_mysql:
        try:
            # 解析数据库URL获取数据库名
            db_name = DATABASE_URL.split('/')[-1]
            base_url = DATABASE_URL.rsplit('/', 1)[0]
            
            # 连接MySQL服务器 (不指定数据库)
            temp_engine = create_engine(base_url + '/mysql')
            with temp_engine.connect() as conn:
                # 创建数据库 (如果不存在)
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
            
            temp_engine.dispose()
            print(f"✅ 数据库 '{db_name}' 创建成功")
            
        except Exception as e:
            print(f"⚠️  数据库创建警告: {e}")
    
    elif settings.is_sqlite:
        # 确保SQLite文件目录存在
        db_path = Path(DATABASE_URL.replace('sqlite:///', ''))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"✅ SQLite数据库路径准备完成: {db_path}")

def create_tables():
    """
    创建所有数据表 (同步，更稳定)
    """
    try:
        # 先创建数据库
        create_database()
        
        # 导入所有模型 (确保模型被注册)
        from app.models import (
            User, Project, Supplier, Task, ProjectFile, 
            ProjectStatusLog, FinancialRecord, AIConversation, SystemConfig
        )
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建完成")
        
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        raise

async def create_tables_async():
    """
    创建所有数据表 (异步)
    """
    try:
        # 导入所有模型
        from app.models import (
            User, Project, Supplier, Task, ProjectFile, 
            ProjectStatusLog, FinancialRecord, AIConversation, SystemConfig
        )
        
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ 数据库表创建完成 (异步)")
        
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        raise

# 🧹 数据库清理函数
def drop_tables():
    """删除所有数据表 (危险操作!)"""
    if settings.DEBUG:
        Base.metadata.drop_all(bind=engine)
        print("🗑️  数据库表已删除 (仅开发环境)")
    else:
        print("❌ 生产环境禁止删除表操作")

# 🔍 数据库连接测试
def test_connection() -> bool:
    """测试数据库连接"""
    try:
        with engine.connect() as conn:
            if settings.is_sqlite:
                result = conn.execute(text("SELECT 1"))
            else:
                result = conn.execute(text("SELECT 1 as test"))
            
            test_val = result.fetchone()[0]
            if test_val == 1:
                print("✅ 数据库连接测试通过")
                return True
            else:
                print("❌ 数据库连接测试失败")
                return False
                
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        return False

async def test_async_connection() -> bool:
    """测试异步数据库连接"""
    try:
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_val = result.fetchone()[0]
            
            if test_val == 1:
                print("✅ 异步数据库连接测试通过")
                return True
            else:
                print("❌ 异步数据库连接测试失败")
                return False
                
    except Exception as e:
        print(f"❌ 异步数据库连接错误: {e}")
        return False

# 📈 数据库状态监控
def get_db_status() -> dict:
    """获取数据库状态信息"""
    try:
        with engine.connect() as conn:
            if settings.is_mysql:
                # MySQL状态查询
                try:
                    result = conn.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
                    connections = result.fetchone()[1]
                    
                    result = conn.execute(text("SELECT DATABASE() as current_db"))
                    current_db = result.fetchone()[0]
                    
                    return {
                        "type": "MySQL",
                        "status": "connected",
                        "current_database": current_db,
                        "active_connections": connections,
                        "url": DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else "localhost"
                    }
                except Exception:
                    return {
                        "type": "MySQL",
                        "status": "connected",
                        "current_database": "unknown",
                        "active_connections": "unknown",
                        "url": DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else "localhost"
                    }
            else:
                # SQLite状态
                db_path = Path(DATABASE_URL.replace('sqlite:///', ''))
                return {
                    "type": "SQLite",
                    "status": "connected",
                    "database_file": str(db_path),
                    "file_size": f"{db_path.stat().st_size / 1024:.2f} KB" if db_path.exists() else "0 KB",
                    "readonly": not os.access(db_path.parent, os.W_OK) if db_path.parent.exists() else True
                }
                
    except Exception as e:
        return {
            "type": "unknown",
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    """数据库测试脚本"""
    print("🔧 AI管理系统数据库测试")
    print("=" * 50)
    
    # 配置信息
    print(f"数据库URL: {DATABASE_URL}")
    print(f"数据库类型: {'MySQL' if settings.is_mysql else 'SQLite'}")
    print(f"异步URL: {ASYNC_DATABASE_URL}")
    
    # 连接测试
    if test_connection():
        # 获取状态
        status = get_db_status()
        print(f"数据库状态: {status}")
        
        # 创建表
        create_tables()
        
        # 测试异步连接
        asyncio.run(test_async_connection())
    
    print("=" * 50)