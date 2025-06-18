#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - API路由包初始化
定义API版本和通用响应格式
"""

from fastapi import APIRouter
from app.schemas import ResponseBase, ResponseData

# API版本信息
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# 通用API响应
def success_response(data=None, message="操作成功"):
    """成功响应"""
    if data is not None:
        return ResponseData(success=True, message=message, data=data)
    else:
        return ResponseBase(success=True, message=message)

def error_response(message="操作失败", status_code=400):
    """错误响应"""
    return ResponseBase(success=False, message=message)

# API路由器工厂
def create_api_router() -> APIRouter:
    """创建API路由器"""
    router = APIRouter(prefix=API_PREFIX)
    return router

# API标签定义
API_TAGS = {
    "auth": "用户认证",
    "users": "用户管理", 
    "projects": "项目管理",
    "tasks": "任务管理",
    "suppliers": "供应商管理",
    "files": "文件管理",
    "reports": "报告统计",
    "system": "系统管理"
}

# 导出
__all__ = [
    "API_VERSION",
    "API_PREFIX", 
    "API_TAGS",
    "success_response",
    "error_response",
    "create_api_router"
]