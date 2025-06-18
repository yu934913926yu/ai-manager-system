#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - SQLAlchemy数据库模型
定义所有数据表结构，支持完整的项目管理业务流程
"""

from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Decimal as SQLDecimal,
    Boolean, ForeignKey, Enum as SQLEnum, JSON, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

from app.database import Base
from app import StatusEnum, RoleEnum, FileTypeEnum

# 🏗️ 用户表 (核心表)
class User(Base):
    """用户表 - 管理系统用户和权限"""
    __tablename__ = "users"
    
    # 主键和基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, comment="邮箱")
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False, comment="密码哈希")
    
    # 用户信息
    full_name: Mapped[Optional[str]] = mapped_column(String(100), comment="真实姓名")
    phone: Mapped[Optional[str]] = mapped_column(String(20), comment="手机号")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), comment="头像URL")
    
    # 角色和权限
    role: Mapped[str] = mapped_column(
        SQLEnum(RoleEnum.ADMIN, RoleEnum.DESIGNER, RoleEnum.FINANCE, RoleEnum.SALES, name="user_role"),
        default=RoleEnum.DESIGNER,
        comment="用户角色"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否管理员")
    
    # 企业微信信息
    wechat_userid: Mapped[Optional[str]] = mapped_column(String(100), unique=True, comment="企业微信用户ID")
    wechat_name: Mapped[Optional[str]] = mapped_column(String(100), comment="企业微信姓名")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="最后登录时间")
    
    # 关系映射
    created_projects: Mapped[List["Project"]] = relationship("Project", foreign_keys="Project.creator_id", back_populates="creator")
    assigned_projects: Mapped[List["Project"]] = relationship("Project", foreign_keys="Project.designer_id", back_populates="designer")
    created_tasks: Mapped[List["Task"]] = relationship("Task", foreign_keys="Task.creator_id", back_populates="creator")
    assigned_tasks: Mapped[List["Task"]] = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    uploaded_files: Mapped[List["ProjectFile"]] = relationship("ProjectFile", back_populates="uploader")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# 📊 项目表 (核心业务表)
class Project(Base):
    """项目表 - 管理所有项目信息和状态"""
    __tablename__ = "projects"
    
    # 主键和基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="项目编号")
    project_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="项目描述")
    
    # 客户信息
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="客户名称")
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), comment="客户电话")
    customer_email: Mapped[Optional[str]] = mapped_column(String(100), comment="客户邮箱")
    customer_company: Mapped[Optional[str]] = mapped_column(String(100), comment="客户公司")
    
    # 项目状态和流程
    status: Mapped[str] = mapped_column(
        SQLEnum(
            StatusEnum.PENDING_QUOTE, StatusEnum.QUOTED, StatusEnum.CONFIRMED,
            StatusEnum.DEPOSIT_PAID, StatusEnum.IN_DESIGN, StatusEnum.PENDING_APPROVAL,
            StatusEnum.APPROVED, StatusEnum.IN_PRODUCTION, StatusEnum.COMPLETED,
            StatusEnum.PAID, StatusEnum.ARCHIVED,
            name="project_status"
        ),
        default=StatusEnum.PENDING_QUOTE,
        index=True,
        comment="项目状态"
    )
    priority: Mapped[str] = mapped_column(String(20), default="normal", comment="优先级: low/normal/high/urgent")
    
    # 财务信息
    quoted_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 2), comment="报价金额")
    final_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 2), comment="最终成交金额")
    cost_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 2), comment="成本金额")
    deposit_amount: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 2), comment="定金金额")
    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False, comment="定金是否已付")
    final_paid: Mapped[bool] = mapped_column(Boolean, default=False, comment="尾款是否已付")
    
    # 时间管理
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    deadline: Mapped[Optional[date]] = mapped_column(Date, comment="项目截止日期")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="项目开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="项目完成时间")
    
    # 人员分配
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    designer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), comment="设计师ID")
    sales_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), comment="销售人员ID")
    
    # 项目分类和标签
    category: Mapped[Optional[str]] = mapped_column(String(50), comment="项目类别")
    tags: Mapped[Optional[str]] = mapped_column(JSON, comment="项目标签(JSON数组)")
    
    # 备注和特殊说明
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="项目备注")
    customer_feedback: Mapped[Optional[str]] = mapped_column(Text, comment="客户反馈")
    
    # 关系映射
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id], back_populates="created_projects")
    designer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[designer_id], back_populates="assigned_projects")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    files: Mapped[List["ProjectFile"]] = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    status_logs: Mapped[List["ProjectStatusLog"]] = relationship("ProjectStatusLog", back_populates="project", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_project_customer_status', 'customer_name', 'status'),
        Index('idx_project_dates', 'created_at', 'deadline'),
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.project_name}', status='{self.status}')>"


# 🏢 供应商表
class Supplier(Base):
    """供应商表 - 管理外部供应商信息"""
    __tablename__ = "suppliers"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="供应商名称")
    company_name: Mapped[Optional[str]] = mapped_column(String(150), comment="公司全称")
    
    # 联系信息
    contact_person: Mapped[Optional[str]] = mapped_column(String(50), comment="联系人")
    phone: Mapped[Optional[str]] = mapped_column(String(20), comment="联系电话")
    email: Mapped[Optional[str]] = mapped_column(String(100), comment="邮箱")
    address: Mapped[Optional[str]] = mapped_column(Text, comment="地址")
    
    # 业务信息
    service_type: Mapped[Optional[str]] = mapped_column(String(100), comment="服务类型")
    business_scope: Mapped[Optional[str]] = mapped_column(Text, comment="经营范围")
    
    # 合作信息
    rating: Mapped[int] = mapped_column(Integer, default=5, comment="合作评分(1-10)")
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否优选供应商")
    cooperation_years: Mapped[Optional[int]] = mapped_column(Integer, comment="合作年限")
    
    # 财务信息
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), comment="付款条款")
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(12, 2), comment="信用额度")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 关系映射
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="supplier")
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}', rating={self.rating})>"


# 📋 任务表
class Task(Base):
    """任务表 - 管理项目中的具体任务"""
    __tablename__ = "tasks"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="任务标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="任务描述")
    
    # 关联信息
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="所属项目ID")
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), comment="执行人ID")
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("suppliers.id"), comment="供应商ID")
    
    # 任务状态
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="任务状态: pending/in_progress/completed/cancelled")
    priority: Mapped[str] = mapped_column(String(20), default="normal", comment="优先级")
    
    # 时间管理
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    due_date: Mapped[Optional[date]] = mapped_column(Date, comment="截止日期")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")
    
    # 财务信息
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 2), comment="预估成本")
    actual_cost: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 2), comment="实际成本")
    
    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="任务备注")
    
    # 关系映射
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"


# 📁 项目文件表
class ProjectFile(Base):
    """项目文件表 - 管理项目相关的所有文件"""
    __tablename__ = "project_files"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件路径")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="文件大小(字节)")
    file_type: Mapped[str] = mapped_column(
        SQLEnum(
            FileTypeEnum.IMAGE, FileTypeEnum.DOCUMENT, FileTypeEnum.DESIGN,
            FileTypeEnum.CONTRACT, FileTypeEnum.OTHER,
            name="file_type"
        ),
        default=FileTypeEnum.OTHER,
        comment="文件类型"
    )
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), comment="MIME类型")
    
    # 关联信息
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="所属项目ID")
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="上传人ID")
    task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tasks.id"), comment="关联任务ID")
    
    # 文件属性
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否公开")
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为最终版本")
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")
    
    # 描述和标签
    description: Mapped[Optional[str]] = mapped_column(Text, comment="文件描述")
    tags: Mapped[Optional[str]] = mapped_column(JSON, comment="文件标签")
    
    # 时间戳
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="上传时间")
    
    # 关系映射
    project: Mapped["Project"] = relationship("Project", back_populates="files")
    uploader: Mapped["User"] = relationship("User", back_populates="uploaded_files")
    
    def __repr__(self):
        return f"<ProjectFile(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"


# 📊 项目状态变更日志表
class ProjectStatusLog(Base):
    """项目状态变更日志表 - 记录项目状态的所有变更"""
    __tablename__ = "project_status_logs"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="项目ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="操作人ID")
    
    # 状态变更信息
    from_status: Mapped[Optional[str]] = mapped_column(String(50), comment="原状态")
    to_status: Mapped[str] = mapped_column(String(50), nullable=False, comment="新状态")
    
    # 变更详情
    change_reason: Mapped[Optional[str]] = mapped_column(String(200), comment="变更原因")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="变更时间")
    
    # 关系映射
    project: Mapped["Project"] = relationship("Project", back_populates="status_logs")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self):
        return f"<ProjectStatusLog(id={self.id}, project_id={self.project_id}, {self.from_status} -> {self.to_status})>"


# 💰 财务记录表
class FinancialRecord(Base):
    """财务记录表 - 管理项目的收支记录"""
    __tablename__ = "financial_records"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="项目ID")
    
    # 财务信息
    record_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="记录类型: income/expense")
    amount: Mapped[Decimal] = mapped_column(SQLDecimal(12, 2), nullable=False, comment="金额")
    currency: Mapped[str] = mapped_column(String(10), default="CNY", comment="币种")
    
    # 分类信息
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="财务类别")
    subcategory: Mapped[Optional[str]] = mapped_column(String(50), comment="子类别")
    
    # 详细信息
    description: Mapped[str] = mapped_column(String(200), nullable=False, comment="描述")
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), comment="参考号/发票号")
    
    # 时间信息
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人")
    
    # 状态
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否确认")
    
    # 关系映射
    project: Mapped["Project"] = relationship("Project")
    creator: Mapped["User"] = relationship("User")
    
    def __repr__(self):
        return f"<FinancialRecord(id={self.id}, type='{self.record_type}', amount={self.amount})>"


# 🤖 AI对话记录表
class AIConversation(Base):
    """AI对话记录表 - 记录企业微信机器人的对话历史"""
    __tablename__ = "ai_conversations"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), comment="用户ID")
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id"), comment="关联项目ID")
    
    # 对话信息
    wechat_userid: Mapped[str] = mapped_column(String(100), nullable=False, comment="企业微信用户ID")
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="消息类型")
    user_message: Mapped[str] = mapped_column(Text, nullable=False, comment="用户消息")
    ai_response: Mapped[str] = mapped_column(Text, nullable=False, comment="AI回复")
    
    # 处理信息
    intent: Mapped[Optional[str]] = mapped_column(String(50), comment="识别的意图")
    confidence: Mapped[Optional[float]] = mapped_column(comment="置信度")
    processing_time: Mapped[Optional[float]] = mapped_column(comment="处理耗时(秒)")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="对话时间")
    
    # 关系映射
    user: Mapped[Optional["User"]] = relationship("User")
    project: Mapped[Optional["Project"]] = relationship("Project")
    
    # 索引
    __table_args__ = (
        Index('idx_conversation_user_time', 'wechat_userid', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AIConversation(id={self.id}, wechat_userid='{self.wechat_userid}', intent='{self.intent}')>"


# 🔧 系统配置表
class SystemConfig(Base):
    """系统配置表 - 存储系统的配置参数"""
    __tablename__ = "system_configs"
    
    # 基本信息
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="配置键")
    config_value: Mapped[str] = mapped_column(Text, comment="配置值")
    config_type: Mapped[str] = mapped_column(String(20), default="string", comment="配置类型")
    
    # 描述信息
    description: Mapped[Optional[str]] = mapped_column(String(200), comment="配置描述")
    category: Mapped[Optional[str]] = mapped_column(String(50), comment="配置分类")
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否可编辑")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.config_key}', value='{self.config_value}')>"


# 📈 项目数据统计视图 (可选)
# 这里可以添加数据库视图定义，用于复杂的统计查询