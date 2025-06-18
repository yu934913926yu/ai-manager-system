#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 配置管理
支持Windows开发环境和宝塔Linux生产环境的配置切换
"""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """系统配置类"""
    
    # 🔧 基础应用配置
    DEBUG: bool = Field(default=True, description="调试模式")
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    
    # 🔐 安全配置
    SECRET_KEY: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="JWT密钥",
        min_length=32
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="JWT过期时间(分钟)")
    
    # 🗄️ 数据库配置 (支持SQLite/MySQL切换)
    DATABASE_URL: str = Field(
        default="sqlite:///./data/ai_manager.db",
        description="数据库连接URL"
    )
    
    # 🤖 AI服务配置
    CLAUDE_API_KEY: Optional[str] = Field(default=None, description="Claude API密钥")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Gemini API密钥")
    OCR_API_KEY: Optional[str] = Field(default=None, description="OCR API密钥")
    
    # AI服务设置
    AI_MAX_TOKENS: int = Field(default=4000, description="AI最大token数")
    AI_TEMPERATURE: float = Field(default=0.7, description="AI温度参数")
    AI_TIMEOUT: int = Field(default=30, description="AI请求超时时间(秒)")
    
    # 📱 企业微信配置
    WECHAT_CORP_ID: Optional[str] = Field(default=None, description="企业微信Corp ID")
    WECHAT_CORP_SECRET: Optional[str] = Field(default=None, description="企业微信Secret")
    WECHAT_AGENT_ID: Optional[str] = Field(default=None, description="企业微信Agent ID")
    
    # 📁 文件存储配置
    UPLOAD_PATH: str = Field(default="./data/uploads", description="文件上传路径")
    BACKUP_PATH: str = Field(default="./data/backups", description="备份文件路径")
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="最大文件大小(字节)")  # 10MB
    
    # 🌐 域名配置 (宝塔部署用)
    DOMAIN: Optional[str] = Field(default=None, description="域名")
    SSL_CERT_PATH: Optional[str] = Field(default=None, description="SSL证书路径")
    
    # 📊 Redis配置 (可选)
    REDIS_URL: Optional[str] = Field(default=None, description="Redis连接URL")
    
    # 📝 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FILE: str = Field(default="logs/ai_manager.log", description="日志文件路径")
    
    @validator('DATABASE_URL')
    def validate_database_url(cls, v):
        """验证数据库URL格式"""
        if not v.startswith(('sqlite:', 'mysql:', 'postgresql:')):
            raise ValueError('数据库URL必须以sqlite:、mysql:或postgresql:开头')
        return v
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        """验证密钥强度"""
        if len(v) < 32:
            raise ValueError('SECRET_KEY长度不能少于32个字符')
        return v
    
    @property
    def is_sqlite(self) -> bool:
        """判断是否使用SQLite数据库"""
        return self.DATABASE_URL.startswith('sqlite:')
    
    @property
    def is_mysql(self) -> bool:
        """判断是否使用MySQL数据库"""
        return self.DATABASE_URL.startswith('mysql:')
    
    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.DEBUG
    
    @property
    def upload_dir(self) -> Path:
        """获取上传目录路径对象"""
        return Path(self.UPLOAD_PATH)
    
    @property
    def backup_dir(self) -> Path:
        """获取备份目录路径对象"""
        return Path(self.BACKUP_PATH)
    
    def get_database_config(self) -> dict:
        """获取数据库配置字典"""
        if self.is_sqlite:
            return {
                "echo": self.DEBUG,  # 开发环境显示SQL
                "pool_pre_ping": True,
                "connect_args": {"check_same_thread": False}  # SQLite特殊配置
            }
        else:
            return {
                "echo": self.DEBUG,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600  # 1小时回收连接
            }
    
    class Config:
        """Pydantic配置"""
        env_file = ".env"  # 从.env文件读取环境变量
        env_file_encoding = 'utf-8'
        case_sensitive = True  # 区分大小写


class DevelopmentSettings(Settings):
    """开发环境配置"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./data/ai_manager.db"


class ProductionSettings(Settings):
    """生产环境配置 (宝塔部署)"""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    # 生产环境建议使用MySQL
    DATABASE_URL: str = "mysql://ai_user:ai_password@localhost/ai_manager"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例 (带缓存)
    根据环境变量自动选择配置类型
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        print("📊 加载生产环境配置 (宝塔部署)")
        return ProductionSettings()
    else:
        print("🔧 加载开发环境配置 (Windows PowerShell)")
        return DevelopmentSettings()


# 导出配置实例
settings = get_settings()

# 配置验证函数
def validate_config() -> bool:
    """验证配置完整性"""
    try:
        # 检查必要的目录
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查AI服务配置
        if not (settings.CLAUDE_API_KEY or settings.GEMINI_API_KEY):
            print("⚠️  警告: 未配置AI服务API密钥")
        
        # 检查企业微信配置
        if not all([settings.WECHAT_CORP_ID, settings.WECHAT_CORP_SECRET, settings.WECHAT_AGENT_ID]):
            print("⚠️  警告: 企业微信配置不完整")
        
        print("✅ 配置验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False


if __name__ == "__main__":
    """配置测试"""
    print("🔧 AI管理系统配置测试")
    print("=" * 50)
    
    config = get_settings()
    print(f"环境模式: {'生产' if config.is_production else '开发'}")
    print(f"数据库类型: {'MySQL' if config.is_mysql else 'SQLite'}")
    print(f"调试模式: {config.DEBUG}")
    print(f"服务地址: {config.HOST}:{config.PORT}")
    print(f"上传目录: {config.UPLOAD_PATH}")
    
    # 验证配置
    validate_config()