#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - Pydantic数据模式
定义API请求响应的数据验证模型
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, validator
from app import StatusEnum, RoleEnum

# ==================== 基础响应模型 ====================

class ResponseBase(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    code: int = 200
    
class ResponseData(ResponseBase):
    """带数据的响应模型"""
    data: Any

class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int
    page_size: int
    total: int
    total_pages: int

class PaginatedResponse(ResponseBase):
    """分页响应模型"""
    data: List[Any]
    meta: PaginationMeta

# ==================== 用户相关模型 ====================

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: RoleEnum = RoleEnum.VIEWER
    wechat_userid: Optional[str] = None
    wechat_name: Optional[str] = None

class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=6)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

# ==================== 项目相关模型 ====================

class ProjectBase(BaseModel):
    """项目基础模型"""
    project_name: str = Field(..., min_length=1, max_length=200)
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    project_type: Optional[str] = None
    priority: str = "normal"
    quoted_price: Optional[float] = Field(None, ge=0)
    deadline: Optional[date] = None
    requirements: Optional[str] = None
    notes: Optional[str] = None

class ProjectCreate(ProjectBase):
    """项目创建模型"""
    designer_id: Optional[int] = None
    sales_id: Optional[int] = None

class ProjectUpdate(BaseModel):
    """项目更新模型"""
    project_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    project_type: Optional[str] = None
    priority: Optional[str] = None
    quoted_price: Optional[float] = Field(None, ge=0)
    cost_price: Optional[float] = Field(None, ge=0)
    deadline: Optional[date] = None
    requirements: Optional[str] = None
    notes: Optional[str] = None
    designer_id: Optional[int] = None
    sales_id: Optional[int] = None

class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int
    project_number: str
    status: str
    cost_price: float
    deposit_amount: float
    final_amount: float
    deposit_paid: bool
    final_paid: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # 关联信息
    creator_id: int
    designer_id: Optional[int]
    sales_id: Optional[int]
    
    # 关联对象
    creator: Optional[UserResponse]
    designer: Optional[UserResponse]
    sales: Optional[UserResponse]
    
    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    """项目详情响应模型"""
    tasks: List["TaskResponse"] = []
    files: List["FileResponse"] = []
    status_logs: List["StatusLogResponse"] = []

class ProjectStatusUpdate(BaseModel):
    """项目状态更新模型"""
    status: str
    reason: Optional[str] = None

class ProjectListResponse(BaseModel):
    """项目列表响应模型"""
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int

# ==================== 任务相关模型 ====================

class TaskBase(BaseModel):
    """任务基础模型"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    task_type: Optional[str] = None
    priority: str = "normal"
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, ge=0)

class TaskCreate(TaskBase):
    """任务创建模型"""
    project_id: int
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    """任务更新模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    assignee_id: Optional[int] = None

class TaskResponse(TaskBase):
    """任务响应模型"""
    id: int
    status: str
    actual_hours: Optional[float]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # 关联信息
    project_id: int
    assignee_id: Optional[int]
    creator_id: int
    
    # 关联对象
    project: Optional["ProjectResponse"]
    assignee: Optional[UserResponse]
    creator: Optional[UserResponse]
    
    class Config:
        from_attributes = True

# ==================== 供应商相关模型 ====================

class SupplierBase(BaseModel):
    """供应商基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    company_name: Optional[str] = None
    service_type: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    rating: int = Field(5, ge=1, le=10)
    is_preferred: bool = False
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    """供应商创建模型"""
    pass

class SupplierUpdate(BaseModel):
    """供应商更新模型"""
    name: Optional[str] = None
    company_name: Optional[str] = None
    service_type: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=10)
    is_preferred: Optional[bool] = None
    notes: Optional[str] = None

class SupplierResponse(SupplierBase):
    """供应商响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==================== 文件相关模型 ====================

class FileUpload(BaseModel):
    """文件上传模型"""
    project_id: int
    description: Optional[str] = None

class FileResponse(BaseModel):
    """文件响应模型"""
    id: int
    filename: str
    file_path: str
    file_size: int
    file_type: str
    uploaded_at: datetime
    uploader: Optional[UserResponse]
    
    class Config:
        from_attributes = True

# ==================== 状态日志模型 ====================

class StatusLogResponse(BaseModel):
    """状态日志响应模型"""
    id: int
    from_status: str
    to_status: str
    change_reason: Optional[str]
    created_at: datetime
    user: Optional[UserResponse]
    
    class Config:
        from_attributes = True

# ==================== AI对话模型 ====================

class AIMessageRequest(BaseModel):
    """AI消息请求模型"""
    message: str
    context: Optional[Dict[str, Any]] = None

class AIMessageResponse(BaseModel):
    """AI消息响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    processing_time: float

# ==================== 统计报告模型 ====================

class ProjectStatistics(BaseModel):
    """项目统计模型"""
    total: int
    ongoing: int
    completed: int
    overdue: int
    this_month: int
    revenue: float
    cost: float
    profit: float

class DashboardData(BaseModel):
    """仪表盘数据模型"""
    project_stats: ProjectStatistics
    recent_projects: List[ProjectResponse]
    pending_tasks: List[TaskResponse]
    activities: List[Dict[str, Any]]

# 更新前向引用
ProjectDetailResponse.model_rebuild()
TaskResponse.model_rebuild()