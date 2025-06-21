#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 应用包初始化
定义全局常量和枚举类型
"""

from enum import Enum

# 版本信息
__version__ = "1.0.0"
__author__ = "AI Manager Team"
__email__ = "support@ai-manager.com"

# 项目状态枚举
class StatusEnum(str, Enum):
    """项目状态枚举"""
    PENDING_QUOTE = "待报价"
    QUOTED = "已报价"
    CONFIRMED = "客户确认"
    DEPOSIT_PAID = "定金已付"
    IN_DESIGN = "设计中"
    PENDING_CONFIRM = "待客户确认"
    CUSTOMER_CONFIRMED = "客户定稿"
    IN_PRODUCTION = "生产中"
    COMPLETED = "项目完成"
    FINAL_PAID = "尾款已付"
    ARCHIVED = "已归档"
    CANCELLED = "已取消"

# 用户角色枚举
class RoleEnum(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"        # 管理员
    DESIGNER = "designer"  # 设计师
    FINANCE = "finance"    # 财务
    SALES = "sales"        # 销售
    VIEWER = "viewer"      # 查看者

# 任务状态枚举
class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    CANCELLED = "cancelled"      # 已取消
    OVERDUE = "overdue"         # 已逾期

# 优先级枚举
class PriorityEnum(str, Enum):
    """优先级枚举"""
    LOW = "low"          # 低
    NORMAL = "normal"    # 正常
    HIGH = "high"        # 高
    URGENT = "urgent"    # 紧急

# 文件类型枚举
class FileTypeEnum(str, Enum):
    """文件类型枚举"""
    IMAGE = "image"      # 图片
    DOCUMENT = "document"  # 文档
    VIDEO = "video"      # 视频
    AUDIO = "audio"      # 音频
    OTHER = "other"      # 其他

# 财务记录类型枚举
class FinancialTypeEnum(str, Enum):
    """财务记录类型枚举"""
    INCOME = "income"     # 收入
    EXPENSE = "expense"   # 支出

# 财务类别枚举
class FinancialCategoryEnum(str, Enum):
    """财务类别枚举"""
    DEPOSIT = "deposit"              # 定金
    FINAL_PAYMENT = "final_payment"  # 尾款
    SUPPLIER_COST = "supplier_cost"  # 供应商成本
    OTHER_INCOME = "other_income"    # 其他收入
    OTHER_EXPENSE = "other_expense"  # 其他支出

# 供应商服务类型
class SupplierServiceType(str, Enum):
    """供应商服务类型"""
    PRINTING = "印刷"
    PRODUCTION = "制作"
    INSTALLATION = "安装"
    DESIGN = "设计"
    LOGISTICS = "物流"
    OTHER = "其他"

# AI服务提供商
class AIProviderEnum(str, Enum):
    """AI服务提供商枚举"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    GPT4 = "gpt4"
    LOCAL = "local"

# 系统配置键
class ConfigKeyEnum(str, Enum):
    """系统配置键枚举"""
    COMPANY_NAME = "company_name"
    COMPANY_LOGO = "company_logo"
    DEFAULT_DEADLINE_DAYS = "default_deadline_days"
    AUTO_ASSIGN_DESIGNER = "auto_assign_designer"
    ENABLE_WECHAT_NOTIFY = "enable_wechat_notify"
    ENABLE_EMAIL_NOTIFY = "enable_email_notify"
    PROJECT_NUMBER_PREFIX = "project_number_prefix"
    PROJECT_NUMBER_FORMAT = "project_number_format"

# 通知类型
class NotificationTypeEnum(str, Enum):
    """通知类型枚举"""
    PROJECT_CREATED = "project_created"
    PROJECT_ASSIGNED = "project_assigned"
    STATUS_CHANGED = "status_changed"
    DEADLINE_WARNING = "deadline_warning"
    PAYMENT_REMINDER = "payment_reminder"
    TASK_ASSIGNED = "task_assigned"
    OVERDUE_ALERT = "overdue_alert"

# 导出所有枚举
__all__ = [
    "StatusEnum",
    "RoleEnum",
    "TaskStatusEnum",
    "PriorityEnum",
    "FileTypeEnum",
    "FinancialTypeEnum",
    "FinancialCategoryEnum",
    "SupplierServiceType",
    "AIProviderEnum",
    "ConfigKeyEnum",
    "NotificationTypeEnum",
    "__version__",
    "__author__",
    "__email__"
]