#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 应用包初始化
定义应用级别的常量、版本信息和通用工具
"""

import os
import sys
from pathlib import Path

# 版本信息
__version__ = "1.0.0"
__author__ = "AI管理系统开发团队"
__description__ = "基于AI的企业级项目管理系统"

# 应用基础信息
APP_NAME = "AI Manager System"
APP_VERSION = __version__
APP_DESCRIPTION = __description__

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = Path(__file__).parent.parent
APP_ROOT = Path(__file__).parent

# 添加项目根目录到Python路径 (确保可以导入模块)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 通用常量
class StatusEnum:
    """项目状态枚举"""
    PENDING_QUOTE = "待报价"          # 初始状态
    QUOTED = "已报价"                # 已给出报价
    CONFIRMED = "客户确认"            # 客户确认报价
    DEPOSIT_PAID = "定金已付"         # 定金到账
    IN_DESIGN = "设计中"             # 设计进行中
    PENDING_APPROVAL = "待客户确认"    # 等待客户确认设计
    APPROVED = "客户定稿"            # 客户确认设计稿
    IN_PRODUCTION = "生产中"         # 投入生产
    COMPLETED = "项目完成"           # 项目交付完成
    PAID = "尾款已付"               # 尾款到账
    ARCHIVED = "已归档"             # 项目归档

class RoleEnum:
    """用户角色枚举"""
    ADMIN = "admin"                 # 管理员 (老板)
    DESIGNER = "designer"           # 设计师
    FINANCE = "finance"             # 财务
    SALES = "sales"                 # 销售

class FileTypeEnum:
    """文件类型枚举"""
    IMAGE = "image"                 # 图片文件
    DOCUMENT = "document"           # 文档文件
    DESIGN = "design"               # 设计文件
    CONTRACT = "contract"           # 合同文件
    OTHER = "other"                # 其他文件

# AI服务常量
class AIConstants:
    """AI服务相关常量"""
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    TIMEOUT = 30
    
    # OCR相关
    OCR_SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
    OCR_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # 提示词模板标识
    PROMPT_PROJECT_ANALYSIS = "project_analysis"
    PROMPT_OCR_EXTRACT = "ocr_extract"
    PROMPT_STATUS_UPDATE = "status_update"

# 企业微信常量
class WeChatConstants:
    """企业微信相关常量"""
    MESSAGE_TYPE_TEXT = "text"
    MESSAGE_TYPE_IMAGE = "image"
    MESSAGE_TYPE_FILE = "file"
    
    # 机器人指令
    COMMANDS = {
        "help": "帮助",
        "create": "创建项目",
        "update": "更新状态",
        "query": "查询项目",
        "upload": "上传文件"
    }

# 工具函数
def get_app_info() -> dict:
    """获取应用信息"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "author": __author__,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "project_root": str(PROJECT_ROOT),
        "backend_root": str(BACKEND_ROOT),
        "app_root": str(APP_ROOT)
    }

def is_windows() -> bool:
    """判断是否为Windows系统"""
    return os.name == 'nt'

def is_linux() -> bool:
    """判断是否为Linux系统"""
    return os.name == 'posix'

def get_safe_path(*args) -> Path:
    """获取跨平台安全路径"""
    return Path(*args)

# 验证应用环境
def validate_environment() -> bool:
    """验证应用运行环境"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("❌ Python版本过低，要求3.8+")
            return False
        
        # 检查必要目录
        required_dirs = [
            PROJECT_ROOT / "data",
            PROJECT_ROOT / "data" / "uploads",
            PROJECT_ROOT / "data" / "backups",
            BACKEND_ROOT / "logs"
        ]
        
        for dir_path in required_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        print("✅ 应用环境验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 应用环境验证失败: {e}")
        return False

# 模块导出
__all__ = [
    "__version__",
    "__author__", 
    "__description__",
    "APP_NAME",
    "APP_VERSION",
    "APP_DESCRIPTION",
    "PROJECT_ROOT",
    "BACKEND_ROOT", 
    "APP_ROOT",
    "StatusEnum",
    "RoleEnum", 
    "FileTypeEnum",
    "AIConstants",
    "WeChatConstants",
    "get_app_info",
    "is_windows",
    "is_linux",
    "get_safe_path",
    "validate_environment"
]

# 初始化应用环境
if __name__ != "__main__":
    # 只有在被导入时才执行环境验证
    validate_environment()

# 调试信息
if __name__ == "__main__":
    print("🔧 AI管理系统应用包信息")
    print("=" * 50)
    
    info = get_app_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print("\n📁 目录结构:")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"后端根目录: {BACKEND_ROOT}")
    print(f"应用根目录: {APP_ROOT}")
    
    print(f"\n🖥️  系统信息:")
    print(f"操作系统: {'Windows' if is_windows() else 'Linux/Unix'}")
    print(f"Python版本: {sys.version}")
    
    print("\n🔧 环境验证:")
    validate_environment()
    
    print("=" * 50)