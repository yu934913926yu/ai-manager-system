#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - FastAPI应用入口
支持Windows PowerShell开发环境和宝塔Linux生产环境
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径 (兼容Windows和Linux)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import engine, create_tables, test_connection

# 获取配置
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 AI管理系统启动中...")
    
    # 检查数据库连接
    if not test_connection():
        print("❌ 数据库连接失败")
        raise Exception("Database connection failed")
    
    # 创建数据库表 (同步方式，更稳定)
    try:
        create_tables()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise
    
    # 创建必要的目录
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    os.makedirs(settings.BACKUP_PATH, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    print("📁 目录结构初始化完成")
    
    yield
    
    # 关闭时执行
    print("🔴 AI管理系统关闭")

# 创建FastAPI应用
app = FastAPI(
    title="AI管理系统",
    description="基于AI的企业级项目管理系统",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [f"https://{settings.DOMAIN}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务 (用于文件上传)
if os.path.exists(settings.UPLOAD_PATH):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_PATH), name="uploads")

# 注册API路由
try:
    from app.api import projects, tasks, suppliers
    from app.api import create_api_router
    
    # 创建API路由器
    api_router = create_api_router()
    
    # 注册各模块路由
    api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
    api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
    api_router.include_router(suppliers.router, prefix="/suppliers", tags=["供应商管理"])
    
    # 注册到主应用
    app.include_router(api_router)
    print("✅ API路由注册完成")
    
except ImportError as e:
    print(f"⚠️ API路由注册跳过: {e}")

# 根路由 - 健康检查
@app.get("/")
async def root():
    """根路由 - 返回系统状态"""
    return {
        "message": "🤖 AI管理系统运行正常",
        "version": "1.0.0",
        "environment": "development" if settings.DEBUG else "production",
        "database": "连接正常" if test_connection() else "连接失败"
    }

# 健康检查路由
@app.get("/health")
async def health_check():
    """健康检查接口 - 供宝塔监控使用"""
    try:
        db_status = test_connection()
        return {
            "status": "healthy" if db_status else "unhealthy",
            "timestamp": str(Path(__file__).stat().st_mtime),
            "database": "ok" if db_status else "error",
            "ai_service": "pending"  # 第7轮后会更新
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"系统异常: {str(e)}")

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    print(f"❌ 全局异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "系统内部错误",
            "detail": str(exc) if settings.DEBUG else "请联系系统管理员"
        }
    )

def main():
    """主函数 - 兼容Windows PowerShell和宝塔部署"""
    print("🔧 启动配置:")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   HOST: {settings.HOST}")
    print(f"   PORT: {settings.PORT}")
    print(f"   DATABASE: {settings.DATABASE_URL}")
    
    # 启动应用
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,  # 开发环境自动重载
        workers=1 if settings.DEBUG else 4,  # 生产环境多进程
        log_level="info"
    )

if __name__ == "__main__":
    main()