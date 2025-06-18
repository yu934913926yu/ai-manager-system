#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - Pydantic数据验证模型
定义API请求和响应的数据结构，用于数据验证和序列化
"""

from datetime import datetime, date
from typing import List, Optional, Union
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, EmailStr, validator, Field, ConfigDict
from app import StatusEnum, RoleEnum, FileTypeEnum

# 🔧 基础配置类
class BaseSchema(BaseModel):
    """基础Schema配置"""
    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM模型创建
        use_enum_values=True,  # 使用枚举值而非枚举对象
        validate_assignment=True,  # 赋值时验证
        arbitrary_types_allowed=True  # 允许任意类型
    )

# 📊 通用响应模型
class ResponseBase(BaseSchema):
    """API响应基础模型"""
    success: bool = True
    message: str = "操作成功"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ResponseData(ResponseBase):
    """带数据的响应模型"""
    data: Optional[Union[dict, list]] = None

class PaginationMeta(BaseSchema):
    """分页元数据"""
    page: int = Field(ge=1, description="当前页码")
    page_size: int = Field(ge=1, le=100, description="每页大小")
    total: int = Field(ge=0, description="总数量")
    total_pages: int = Field(ge=0, description="总页数")

class PaginatedResponse(ResponseBase):
    """分页响应模型"""
    data: List[dict] = []
    meta: PaginationMeta

# 👤 用户相关模型
class UserBase(BaseSchema):
    """用户基础模型"""
    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="真实姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    role: str = Field(default=RoleEnum.DESIGNER, description="用户角色")
    is_active: bool = Field(default=True, description="是否激活")

class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(min_length=6, max_length=50, description="密码")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度不能少于6位')
        return v

class UserUpdate(BaseSchema):
    """更新用户模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class UserPasswordUpdate(BaseSchema):
    """用户密码更新模型"""
    current_password: str = Field(description="当前密码")
    new_password: str = Field(min_length=6, max_length=50, description="新密码")

class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    avatar_url: Optional[str] = None
    is_admin: bool = False
    wechat_userid: Optional[str] = None
    wechat_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class UserLogin(BaseSchema):
    """用户登录模型"""
    username: str = Field(description="用户名或邮箱")
    password: str = Field(description="密码")

class TokenResponse(BaseSchema):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24小时
    user: UserResponse

# 📊 项目相关模型
class ProjectBase(BaseSchema):
    """项目基础模型"""
    project_name: str = Field(max_length=200, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    customer_name: str = Field(max_length=100, description="客户名称")
    customer_phone: Optional[str] = Field(None, max_length=20, description="客户电话")
    customer_email: Optional[EmailStr] = Field(None, description="客户邮箱")
    customer_company: Optional[str] = Field(None, max_length=100, description="客户公司")
    priority: str = Field(default="normal", description="优先级")
    category: Optional[str] = Field(None, max_length=50, description="项目类别")
    deadline: Optional[date] = Field(None, description="截止日期")

class ProjectCreate(ProjectBase):
    """创建项目模型"""
    designer_id: Optional[int] = Field(None, description="设计师ID")
    quoted_price: Optional[Decimal] = Field(None, ge=0, description="报价金额")
    notes: Optional[str] = Field(None, description="项目备注")

class ProjectUpdate(BaseSchema):
    """更新项目模型"""
    project_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[EmailStr] = None
    customer_company: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    priority: Optional[str] = None
    quoted_price: Optional[Decimal] = Field(None, ge=0)
    final_price: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    deposit_amount: Optional[Decimal] = Field(None, ge=0)
    designer_id: Optional[int] = None
    deadline: Optional[date] = None
    notes: Optional[str] = None
    customer_feedback: Optional[str] = None

class ProjectStatusUpdate(BaseSchema):
    """项目状态更新模型"""
    status: str = Field(description="新状态")
    change_reason: Optional[str] = Field(None, max_length=200, description="变更原因")
    notes: Optional[str] = Field(None, description="备注")

class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int
    project_number: str
    status: str
    quoted_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    deposit_amount: Optional[Decimal] = None
    deposit_paid: bool = False
    final_paid: bool = False
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    creator_id: int
    designer_id: Optional[int] = None
    sales_id: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    customer_feedback: Optional[str] = None

class ProjectListResponse(BaseSchema):
    """项目列表响应模型"""
    id: int
    project_number: str
    project_name: str
    customer_name: str
    status: str
    quoted_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    priority: str
    deadline: Optional[date] = None
    created_at: datetime
    designer_id: Optional[int] = None
    creator_id: int

class ProjectDetailResponse(ProjectResponse):
    """项目详情响应模型"""
    creator: Optional[UserResponse] = None
    designer: Optional[UserResponse] = None
    task_count: int = 0
    file_count: int = 0
    recent_activities: List[dict] = []

# 🏢 供应商相关模型
class SupplierBase(BaseSchema):
    """供应商基础模型"""
    name: str = Field(max_length=100, description="供应商名称")
    company_name: Optional[str] = Field(None, max_length=150, description="公司全称")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    address: Optional[str] = Field(None, description="地址")
    service_type: Optional[str] = Field(None, max_length=100, description="服务类型")
    business_scope: Optional[str] = Field(None, description="经营范围")

class SupplierCreate(SupplierBase):
    """创建供应商模型"""
    rating: int = Field(default=5, ge=1, le=10, description="合作评分")
    payment_terms: Optional[str] = Field(None, max_length=100, description="付款条款")
    notes: Optional[str] = Field(None, description="备注")

class SupplierUpdate(BaseSchema):
    """更新供应商模型"""
    name: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=150)
    contact_person: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    service_type: Optional[str] = Field(None, max_length=100)
    business_scope: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=10)
    is_preferred: Optional[bool] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None

class SupplierResponse(SupplierBase):
    """供应商响应模型"""
    id: int
    rating: int
    is_preferred: bool
    cooperation_years: Optional[int] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None

# 📋 任务相关模型
class TaskBase(BaseSchema):
    """任务基础模型"""
    title: str = Field(max_length=200, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    priority: str = Field(default="normal", description="优先级")
    due_date: Optional[date] = Field(None, description="截止日期")

class TaskCreate(TaskBase):
    """创建任务模型"""
    project_id: int = Field(description="所属项目ID")
    assignee_id: Optional[int] = Field(None, description="执行人ID")
    supplier_id: Optional[int] = Field(None, description="供应商ID")
    estimated_cost: Optional[Decimal] = Field(None, ge=0, description="预估成本")
    notes: Optional[str] = Field(None, description="任务备注")

class TaskUpdate(BaseSchema):
    """更新任务模型"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    supplier_id: Optional[int] = None
    due_date: Optional[date] = None
    estimated_cost: Optional[Decimal] = Field(None, ge=0)
    actual_cost: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None

class TaskResponse(TaskBase):
    """任务响应模型"""
    id: int
    project_id: int
    creator_id: int
    assignee_id: Optional[int] = None
    supplier_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    notes: Optional[str] = None

# 📁 文件相关模型
class ProjectFileBase(BaseSchema):
    """项目文件基础模型"""
    original_filename: str = Field(description="原始文件名")
    file_type: str = Field(default=FileTypeEnum.OTHER, description="文件类型")
    description: Optional[str] = Field(None, description="文件描述")

class ProjectFileCreate(ProjectFileBase):
    """创建项目文件模型"""
    project_id: int = Field(description="所属项目ID")
    task_id: Optional[int] = Field(None, description="关联任务ID")
    is_public: bool = Field(default=False, description="是否公开")
    is_final: bool = Field(default=False, description="是否为最终版本")
    tags: Optional[List[str]] = Field(None, description="文件标签")

class ProjectFileResponse(ProjectFileBase):
    """项目文件响应模型"""
    id: int
    filename: str
    file_path: str
    file_size: int
    mime_type: Optional[str] = None
    project_id: int
    uploader_id: int
    task_id: Optional[int] = None
    is_public: bool
    is_final: bool
    version: int
    tags: Optional[List[str]] = None
    uploaded_at: datetime

# 💰 财务相关模型
class FinancialRecordBase(BaseSchema):
    """财务记录基础模型"""
    record_type: str = Field(description="记录类型: income/expense")
    amount: Decimal = Field(gt=0, description="金额")
    category: str = Field(max_length=50, description="财务类别")
    description: str = Field(max_length=200, description="描述")
    transaction_date: date = Field(description="交易日期")

class FinancialRecordCreate(FinancialRecordBase):
    """创建财务记录模型"""
    project_id: int = Field(description="项目ID")
    subcategory: Optional[str] = Field(None, max_length=50, description="子类别")
    reference_number: Optional[str] = Field(None, max_length=100, description="参考号")
    currency: str = Field(default="CNY", description="币种")

class FinancialRecordResponse(FinancialRecordBase):
    """财务记录响应模型"""
    id: int
    project_id: int
    subcategory: Optional[str] = None
    reference_number: Optional[str] = None
    currency: str
    is_confirmed: bool
    created_at: datetime
    created_by: int

# 🤖 AI对话相关模型
class AIConversationBase(BaseSchema):
    """AI对话基础模型"""
    wechat_userid: str = Field(description="企业微信用户ID")
    message_type: str = Field(description="消息类型")
    user_message: str = Field(description="用户消息")

class AIConversationCreate(AIConversationBase):
    """创建AI对话模型"""
    ai_response: str = Field(description="AI回复")
    intent: Optional[str] = Field(None, description="识别的意图")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")
    processing_time: Optional[float] = Field(None, ge=0, description="处理耗时")
    project_id: Optional[int] = Field(None, description="关联项目ID")

class AIConversationResponse(AIConversationBase):
    """AI对话响应模型"""
    id: int
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    ai_response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    created_at: datetime

# 📊 统计相关模型
class ProjectStatistics(BaseSchema):
    """项目统计模型"""
    total_projects: int
    active_projects: int
    completed_projects: int
    total_revenue: Decimal
    total_cost: Decimal
    profit_margin: float
    avg_project_duration: Optional[float] = None

class UserStatistics(BaseSchema):
    """用户统计模型"""
    total_users: int
    active_users: int
    designer_count: int
    admin_count: int
    recent_logins: int

class SystemStatistics(BaseSchema):
    """系统统计模型"""
    projects: ProjectStatistics
    users: UserStatistics
    file_count: int
    storage_used: int
    ai_conversations: int
    recent_activities: List[dict]

# 🔍 搜索和过滤模型
class ProjectFilter(BaseSchema):
    """项目过滤模型"""
    status: Optional[str] = None
    priority: Optional[str] = None
    customer_name: Optional[str] = None
    designer_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None

class SearchQuery(BaseSchema):
    """搜索查询模型"""
    query: str = Field(min_length=1, description="搜索关键词")
    type: Optional[str] = Field(None, description="搜索类型")
    filters: Optional[dict] = Field(None, description="搜索过滤条件")

# 🔧 系统配置模型
class SystemConfigBase(BaseSchema):
    """系统配置基础模型"""
    config_key: str = Field(max_length=100, description="配置键")
    config_value: str = Field(description="配置值")
    config_type: str = Field(default="string", description="配置类型")
    description: Optional[str] = Field(None, max_length=200, description="配置描述")
    category: Optional[str] = Field(None, max_length=50, description="配置分类")

class SystemConfigCreate(SystemConfigBase):
    """创建系统配置模型"""
    is_editable: bool = Field(default=True, description="是否可编辑")

class SystemConfigUpdate(BaseSchema):
    """更新系统配置模型"""
    config_value: Optional[str] = None
    description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class SystemConfigResponse(SystemConfigBase):
    """系统配置响应模型"""
    id: int
    is_active: bool
    is_editable: bool
    created_at: datetime
    updated_at: datetime