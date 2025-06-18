#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 项目管理API
提供项目的CRUD操作、状态管理、统计查询等功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db
from app.models import Project, User, ProjectStatusLog
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectDetailResponse, ProjectStatusUpdate, PaginatedResponse,
    PaginationMeta
)
from app.auth import get_current_active_user
from app.permissions import (
    Permission, check_permission, check_project_access,
    check_project_modify, require_project_access, require_project_modify
)
from app.api import success_response, error_response, API_TAGS
from app import StatusEnum
from datetime import datetime, date

router = APIRouter(prefix="/projects", tags=[API_TAGS["projects"]])

# 🔍 项目查询API
@router.get("/", response_model=PaginatedResponse)
async def get_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="项目状态筛选"),
    customer_name: Optional[str] = Query(None, description="客户名称筛选"),
    designer_id: Optional[int] = Query(None, description="设计师ID筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选"),
    date_from: Optional[date] = Query(None, description="开始日期"),
    date_to: Optional[date] = Query(None, description="结束日期"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    
    # 构建查询
    query = db.query(Project)
    
    # 权限过滤 - 非管理员只能看到自己相关的项目
    if not check_permission(current_user, Permission.PROJECT_READ):
        query = query.filter(
            or_(
                Project.creator_id == current_user.id,
                Project.designer_id == current_user.id,
                Project.sales_id == current_user.id
            )
        )
    
    # 状态筛选
    if status:
        query = query.filter(Project.status == status)
    
    # 客户名称筛选
    if customer_name:
        query = query.filter(Project.customer_name.ilike(f"%{customer_name}%"))
    
    # 设计师筛选
    if designer_id:
        query = query.filter(Project.designer_id == designer_id)
    
    # 优先级筛选
    if priority:
        query = query.filter(Project.priority == priority)
    
    # 日期范围筛选
    if date_from:
        query = query.filter(Project.created_at >= date_from)
    if date_to:
        query = query.filter(Project.created_at <= date_to)
    
    # 搜索筛选
    if search:
        search_filter = or_(
            Project.project_name.ilike(f"%{search}%"),
            Project.customer_name.ilike(f"%{search}%"),
            Project.project_number.ilike(f"%{search}%"),
            Project.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # 获取总数
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    # 分页查询
    skip = (page - 1) * page_size
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(page_size).all()
    
    # 转换为响应格式
    project_list = []
    for project in projects:
        project_data = ProjectListResponse.model_validate(project)
        project_list.append(project_data.model_dump())
    
    # 分页元数据
    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )
    
    return PaginatedResponse(
        success=True,
        message=f"获取项目列表成功，共{total}个项目",
        data=project_list,
        meta=meta
    )

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    # 权限检查
    require_project_access(current_user, project)
    
    # 获取关联数据
    task_count = db.query(func.count()).filter_by(project_id=project_id).scalar()
    file_count = db.query(func.count()).filter_by(project_id=project_id).scalar()
    
    # 获取最近活动（状态变更日志）
    recent_activities = db.query(ProjectStatusLog).filter(
        ProjectStatusLog.project_id == project_id
    ).order_by(ProjectStatusLog.created_at.desc()).limit(5).all()
    
    activity_list = []
    for log in recent_activities:
        activity_list.append({
            "id": log.id,
            "from_status": log.from_status,
            "to_status": log.to_status,
            "change_reason": log.change_reason,
            "created_at": log.created_at,
            "user_id": log.user_id
        })
    
    # 构建响应
    project_detail = ProjectDetailResponse.model_validate(project)
    project_detail.task_count = task_count
    project_detail.file_count = file_count
    project_detail.recent_activities = activity_list
    
    return success_response(
        data=project_detail.model_dump(),
        message="获取项目详情成功"
    )

# 🆕 项目创建API
@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新项目"""
    
    # 权限检查
    if not check_permission(current_user, Permission.PROJECT_CREATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有创建项目的权限"
        )
    
    # 生成项目编号
    project_count = db.query(func.count(Project.id)).scalar()
    project_number = f"PRJ{datetime.now().strftime('%Y%m%d')}{project_count + 1:03d}"
    
    # 创建项目
    db_project = Project(
        project_number=project_number,
        project_name=project_data.project_name,
        description=project_data.description,
        customer_name=project_data.customer_name,
        customer_phone=project_data.customer_phone,
        customer_email=project_data.customer_email,
        customer_company=project_data.customer_company,
        priority=project_data.priority,
        category=project_data.category,
        deadline=project_data.deadline,
        quoted_price=project_data.quoted_price,
        designer_id=project_data.designer_id,
        notes=project_data.notes,
        creator_id=current_user.id,
        status=StatusEnum.PENDING_QUOTE,
        created_at=datetime.utcnow()
    )
    
    db.add(db_project)
    db.flush()  # 获取ID
    
    # 记录状态变更日志
    status_log = ProjectStatusLog(
        project_id=db_project.id,
        user_id=current_user.id,
        from_status=None,
        to_status=StatusEnum.PENDING_QUOTE,
        change_reason="项目创建",
        created_at=datetime.utcnow()
    )
    db.add(status_log)
    
    db.commit()
    db.refresh(db_project)
    
    return success_response(
        data=ProjectResponse.model_validate(db_project).model_dump(),
        message=f"项目 {project_number} 创建成功"
    )

# ✏️ 项目更新API
@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新项目信息"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    # 权限检查
    require_project_modify(current_user, project)
    
    # 更新字段
    update_data = project_data.model_dump(exclude_unset=True)
    
    # 检查状态变更
    old_status = project.status
    new_status = update_data.get('status')
    
    for field, value in update_data.items():
        setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    
    # 如果状态发生变更，记录日志
    if new_status and new_status != old_status:
        status_log = ProjectStatusLog(
            project_id=project_id,
            user_id=current_user.id,
            from_status=old_status,
            to_status=new_status,
            change_reason="项目信息更新",
            created_at=datetime.utcnow()
        )
        db.add(status_log)
    
    db.commit()
    db.refresh(project)
    
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(),
        message="项目信息更新成功"
    )

# 🔄 项目状态更新API
@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: int,
    status_data: ProjectStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新项目状态"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    # 权限检查
    if not check_permission(current_user, Permission.PROJECT_STATUS_CHANGE):
        require_project_access(current_user, project)
    
    # 验证状态转换的合法性
    valid_statuses = [
        StatusEnum.PENDING_QUOTE, StatusEnum.QUOTED, StatusEnum.CONFIRMED,
        StatusEnum.DEPOSIT_PAID, StatusEnum.IN_DESIGN, StatusEnum.PENDING_APPROVAL,
        StatusEnum.APPROVED, StatusEnum.IN_PRODUCTION, StatusEnum.COMPLETED,
        StatusEnum.PAID, StatusEnum.ARCHIVED
    ]
    
    if status_data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的项目状态"
        )
    
    old_status = project.status
    
    # 更新状态
    project.status = status_data.status
    project.updated_at = datetime.utcnow()
    
    # 根据状态更新时间戳
    if status_data.status == StatusEnum.IN_DESIGN and not project.started_at:
        project.started_at = datetime.utcnow()
    elif status_data.status == StatusEnum.COMPLETED and not project.completed_at:
        project.completed_at = datetime.utcnow()
    
    # 记录状态变更日志
    status_log = ProjectStatusLog(
        project_id=project_id,
        user_id=current_user.id,
        from_status=old_status,
        to_status=status_data.status,
        change_reason=status_data.change_reason,
        notes=status_data.notes,
        created_at=datetime.utcnow()
    )
    db.add(status_log)
    
    db.commit()
    db.refresh(project)
    
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(),
        message=f"项目状态已从 {old_status} 更新为 {status_data.status}"
    )

# 🗑️ 项目删除API
@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除项目（软删除）"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    # 权限检查
    if not check_permission(current_user, Permission.PROJECT_DELETE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有删除项目的权限"
        )
    
    # 检查项目状态，某些状态下不允许删除
    if project.status in [StatusEnum.IN_DESIGN, StatusEnum.IN_PRODUCTION]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目正在进行中，无法删除"
        )
    
    # 软删除 - 更新状态为已归档
    project.status = StatusEnum.ARCHIVED
    project.updated_at = datetime.utcnow()
    
    # 记录删除日志
    status_log = ProjectStatusLog(
        project_id=project_id,
        user_id=current_user.id,
        from_status=project.status,
        to_status=StatusEnum.ARCHIVED,
        change_reason="项目删除",
        notes="项目已被软删除",
        created_at=datetime.utcnow()
    )
    db.add(status_log)
    
    db.commit()
    
    return success_response(message=f"项目 {project.project_number} 已删除")

# 📊 项目统计API
@router.get("/statistics/overview")
async def get_project_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取项目统计概览"""
    
    # 权限检查
    if not check_permission(current_user, Permission.STATISTICS_VIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有查看统计信息的权限"
        )
    
    # 基础统计
    total_projects = db.query(func.count(Project.id)).scalar()
    
    # 按状态统计
    status_stats = db.query(
        Project.status,
        func.count(Project.id).label('count')
    ).group_by(Project.status).all()
    
    # 财务统计
    revenue_stats = db.query(
        func.sum(Project.final_price).label('total_revenue'),
        func.sum(Project.cost_price).label('total_cost'),
        func.avg(Project.final_price).label('avg_revenue')
    ).filter(Project.final_price.isnot(None)).first()
    
    # 本月新增项目
    from datetime import datetime, timedelta
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_projects = db.query(func.count(Project.id)).filter(
        Project.created_at >= month_start
    ).scalar()
    
    return success_response(
        data={
            "total_projects": total_projects,
            "monthly_new_projects": monthly_projects,
            "status_distribution": dict(status_stats),
            "financial_overview": {
                "total_revenue": float(revenue_stats.total_revenue or 0),
                "total_cost": float(revenue_stats.total_cost or 0),
                "average_revenue": float(revenue_stats.avg_revenue or 0),
                "profit_margin": (
                    (revenue_stats.total_revenue - revenue_stats.total_cost) / revenue_stats.total_revenue * 100
                    if revenue_stats.total_revenue else 0
                )
            }
        },
        message="项目统计信息获取成功"
    )