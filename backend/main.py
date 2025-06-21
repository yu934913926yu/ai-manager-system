#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 数据库模型定义
使用SQLAlchemy ORM定义所有数据表结构
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from app import StatusEnum, RoleEnum

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    full_name = Column(String(100))
    password_hash = Column(String(255), nullable=False)
    
    # 角色和权限
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # 企业微信
    wechat_userid = Column(String(100), unique=True, index=True)
    wechat_name = Column(String(100))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # 关系
    created_projects = relationship("Project", back_populates="creator", foreign_keys="Project.creator_id")
    designed_projects = relationship("Project", back_populates="designer", foreign_keys="Project.designer_id")
    sales_projects = relationship("Project", back_populates="sales", foreign_keys="Project.sales_id")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.creator_id")
    ai_conversations = relationship("AIConversation", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"

class Project(Base):
    """项目模型"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_number = Column(String(50), unique=True, index=True)  # PRJ20240101001
    project_name = Column(String(200), nullable=False)
    customer_name = Column(String(100), nullable=False, index=True)
    customer_phone = Column(String(50))
    customer_email = Column(String(100))
    
    # 项目类型和状态
    project_type = Column(String(50))
    status = Column(String(50), default=StatusEnum.PENDING_QUOTE, index=True)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # 金额
    quoted_price = Column(Float, default=0)
    cost_price = Column(Float, default=0)
    deposit_amount = Column(Float, default=0)
    final_amount = Column(Float, default=0)
    
    # 支付状态
    deposit_paid = Column(Boolean, default=False)
    final_paid = Column(Boolean, default=False)
    
    # 时间相关
    deadline = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 项目描述和需求
    requirements = Column(Text)
    notes = Column(Text)
    
    # 外键关系
    creator_id = Column(Integer, ForeignKey("users.id"))
    designer_id = Column(Integer, ForeignKey("users.id"))
    sales_id = Column(Integer, ForeignKey("users.id"))
    
    # 关系
    creator = relationship("User", back_populates="created_projects", foreign_keys=[creator_id])
    designer = relationship("User", back_populates="designed_projects", foreign_keys=[designer_id])
    sales = relationship("User", back_populates="sales_projects", foreign_keys=[sales_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    status_logs = relationship("ProjectStatusLog", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    financial_records = relationship("FinancialRecord", back_populates="project", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('ix_project_status_customer', 'status', 'customer_name'),
        Index('ix_project_designer_status', 'designer_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Project {self.project_number}: {self.project_name}>"

class Task(Base):
    """任务模型"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    task_type = Column(String(50))  # design, review, production, delivery
    
    # 状态和优先级
    status = Column(String(50), default="pending", index=True)
    priority = Column(String(20), default="normal")
    
    # 时间相关
    due_date = Column(Date)
    estimated_hours = Column(Float)
    actual_hours = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 外键
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    creator_id = Column(Integer, ForeignKey("users.id"))
    
    # 关系
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    
    def __repr__(self):
        return f"<Task {self.title}>"

class Supplier(Base):
    """供应商模型"""
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    company_name = Column(String(200))
    service_type = Column(String(100), index=True)  # 印刷, 制作, 安装等
    
    # 联系信息
    contact_person = Column(String(50))
    phone = Column(String(50))
    email = Column(String(100))
    address = Column(Text)
    
    # 评级和优选
    rating = Column(Integer, default=5)  # 1-10分
    is_preferred = Column(Boolean, default=False)
    
    # 备注
    notes = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    tasks = relationship("Task", secondary="task_suppliers", backref="suppliers")
    
    def __repr__(self):
        return f"<Supplier {self.name}>"

class ProjectStatusLog(Base):
    """项目状态变更日志"""
    __tablename__ = "project_status_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    from_status = Column(String(50))
    to_status = Column(String(50))
    change_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    project = relationship("Project", back_populates="status_logs")
    user = relationship("User")
    
    __table_args__ = (
        Index('ix_status_log_project_created', 'project_id', 'created_at'),
    )

class ProjectFile(Base):
    """项目文件"""
    __tablename__ = "project_files"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    file_type = Column(String(50))
    
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    project = relationship("Project", back_populates="files")
    uploader = relationship("User")

class AIConversation(Base):
    """AI对话记录"""
    __tablename__ = "ai_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    wechat_userid = Column(String(100), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    message_type = Column(String(50))  # text, image, voice
    user_message = Column(Text)
    ai_response = Column(Text)
    
    context_data = Column(Text)  # JSON存储上下文
    processing_time = Column(Float)  # 处理耗时(秒)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 关系
    user = relationship("User", back_populates="ai_conversations")

class FinancialRecord(Base):
    """财务记录"""
    __tablename__ = "financial_records"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    record_type = Column(String(50))  # income, expense
    category = Column(String(50))  # deposit, final_payment, supplier_cost
    amount = Column(Float, nullable=False)
    
    description = Column(Text)
    payment_date = Column(Date)
    
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    project = relationship("Project", back_populates="financial_records")
    creator = relationship("User")

from sqlalchemy import Table

# 多对多关联表
task_suppliers = Table('task_suppliers', Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id')),
    Column('supplier_id', Integer, ForeignKey('suppliers.id'))
)