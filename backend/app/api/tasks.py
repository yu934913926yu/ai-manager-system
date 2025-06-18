#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 任务管理API
提供任务的CRUD操作、状态管理、分配等功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db
from app.models import Task, Project, User, Supplier
from app.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, PaginatedResponse, PaginationMeta
)
from app.auth import get_current_active_user
from app.permissions import Permission, check_permission, check_project_access
from app.api import success_response, error_response, API_TAGS
from datetime import datetime, date

router = APIRouter(prefix="/tasks", tags=[API_TAGS["tasks"]])

# 🔍 任务查询API
@router.get("/", response_model=PaginatedResponse)
async def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    project_id: Optional[int] = Query(None, description="项目ID筛选"),
    assignee_id: Optional[int] = Query(None, description="执行人ID筛选"),
    status: Optional[str] = Query(None, description="任务状态筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选"),
    overdue: Optional[bool] = Query(None, description="是否逾期"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    
    # 构建查询
    query = db.query(Task).join(Project)
    
    # 权限过滤 - 只能看到有权限的项目的任务
    if not check_permission(current_user, Permission.TASK_READ):
        query = query.filter(
            or_(
                Project.creator_id == current_user.id,
                Project.designer_id == current_user.id,
                Task.assignee_id == current_user.id,
                Task.creator_id == current_user.id
            )
        )
    
    # 项目筛选
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    # 执行人筛选
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    
    # 状态筛选
    if status:
        query = query.filter(Task.status == status)
    
    # 优先级筛选
    if priority:
        query = query.filter(Task.priority == priority)
    
    # 逾期筛选
    if overdue is not None:
        today = date.today()
        if overdue:
            query = query.filter(
                and_(Task.due_date < today, Task.status != 'completed')
            )
        else:
            query = query.filter(
                or_(Task.due_date >= today, Task.status == 'completed')
            )
    
    # 搜索筛选
    if search:
        search_filter = or_(
            Task.title.ilike(f"%{search}%"),
            Task.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # 获取总数
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    # 分页查询
    skip = (page - 1) * page_size
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(page_size).all()
    
    # 转换为响应格式
    task_list = []
    for task in tasks:
        task_data = TaskResponse.model_validate(task)
        task_list.append(task_data.model_dump())
    
    # 分页元数据
    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )
    
    return PaginatedResponse(
        success=True,
        message=f"获取任务列表成功，共{total}个任务",
        data=task_list,
        meta=meta
    )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取任务详情"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 权限检查 - 需要有项目访问权限
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if project:
        check_project_access(current_user, project)
    
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message="获取任务详情成功"
    )

# 🆕 任务创建API
@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新任务"""
    
    # 权限检查
    if not check_permission(current_user, Permission.TASK_CREATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有创建任务的权限"
        )
    
    # 验证项目存在
    project = db.query(Project).filter(Project.id == task_data.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联的项目不存在"
        )
    
    # 检查项目权限
    check_project_access(current_user, project)
    
    # 验证执行人存在（如果指定）
    if task_data.assignee_id:
        assignee = db.query(User).filter(User.id == task_data.assignee_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定的执行人不存在"
            )
    
    # 验证供应商存在（如果指定）
    if task_data.supplier_id:
        supplier = db.query(Supplier).filter(Supplier.id == task_data.supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定的供应商不存在"
            )
    
    # 创建任务
    db_task = Task(
        title=task_data.title,
        description=task_data.description,
        project_id=task_data.project_id,
        creator_id=current_user.id,
        assignee_id=task_data.assignee_id,
        supplier_id=task_data.supplier_id,
        priority=task_data.priority,
        due_date=task_data.due_date,
        estimated_cost=task_data.estimated_cost,
        notes=task_data.notes,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return success_response(
        data=TaskResponse.model_validate(db_task).model_dump(),
        message="任务创建成功"
    )

# ✏️ 任务更新API
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新任务信息"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 权限检查 - 创建者、执行者或有任务更新权限的用户可以更新
    can_update = (
        task.creator_id == current_user.id or
        task.assignee_id == current_user.id or
        check_permission(current_user, Permission.TASK_UPDATE)
    )
    
    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有更新任务的权限"
        )
    
    # 更新字段
    update_data = task_data.model_dump(exclude_unset=True)
    
    # 检查状态变更
    old_status = task.status
    new_status = update_data.get('status')
    
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    
    # 根据状态更新时间戳
    if new_status:
        if new_status == 'in_progress' and not task.started_at:
            task.started_at = datetime.utcnow()
        elif new_status == 'completed' and not task.completed_at:
            task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message="任务信息更新成功"
    )

# 🔄 任务状态更新API
@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str = Query(..., description="新状态: pending/in_progress/completed/cancelled"),
    notes: Optional[str] = Query(None, description="状态变更备注"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新任务状态"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 权限检查
    can_update = (
        task.creator_id == current_user.id or
        task.assignee_id == current_user.id or
        check_permission(current_user, Permission.TASK_UPDATE)
    )
    
    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有更新任务状态的权限"
        )
    
    # 验证状态
    valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的任务状态，有效值: {', '.join(valid_statuses)}"
        )
    
    old_status = task.status
    
    # 更新状态
    task.status = status
    task.updated_at = datetime.utcnow()
    
    # 更新时间戳
    if status == 'in_progress' and not task.started_at:
        task.started_at = datetime.utcnow()
    elif status == 'completed' and not task.completed_at:
        task.completed_at = datetime.utcnow()
    
    # 更新备注
    if notes:
        task.notes = f"{task.notes}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}" if task.notes else notes
    
    db.commit()
    db.refresh(task)
    
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message=f"任务状态已从 {old_status} 更新为 {status}"
    )

# 👤 任务分配API
@router.patch("/{task_id}/assign")
async def assign_task(
    task_id: int,
    assignee_id: int = Query(..., description="执行人ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """分配任务给指定用户"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 权限检查
    if not check_permission(current_user, Permission.TASK_ASSIGN):
        # 只有创建者可以分配自己创建的任务
        if task.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有分配任务的权限"
            )
    
    # 验证执行人存在
    assignee = db.query(User).filter(User.id == assignee_id).first()
    if not assignee or not assignee.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定的执行人不存在或未激活"
        )
    
    old_assignee_id = task.assignee_id
    
    # 更新分配
    task.assignee_id = assignee_id
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message=f"任务已分配给 {assignee.full_name or assignee.username}"
    )

# 🗑️ 任务删除API
@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除任务"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 权限检查
    can_delete = (
        task.creator_id == current_user.id or
        check_permission(current_user, Permission.TASK_DELETE)
    )
    
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有删除任务的权限"
        )
    
    # 检查任务状态
    if task.status == 'in_progress':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="进行中的任务无法删除"
        )
    
    task_title = task.title
    
    # 删除任务
    db.delete(task)
    db.commit()
    
    return success_response(message=f"任务 '{task_title}' 已删除")

# 📊 我的任务API
@router.get("/my/tasks", response_model=PaginatedResponse)
async def get_my_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我的任务列表"""
    
    # 查询当前用户相关的任务
    query = db.query(Task).filter(
        or_(
            Task.assignee_id == current_user.id,
            Task.creator_id == current_user.id
        )
    )
    
    # 状态筛选
    if status:
        query = query.filter(Task.status == status)
    
    # 获取总数
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    # 分页查询
    skip = (page - 1) * page_size
    tasks = query.order_by(Task.due_date.asc()).offset(skip).limit(page_size).all()
    
    # 转换为响应格式
    task_list = []
    for task in tasks:
        task_data = TaskResponse.model_validate(task)
        task_list.append(task_data.model_dump())
    
    # 分页元数据
    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )
    
    return PaginatedResponse(
        success=True,
        message=f"获取我的任务列表成功，共{total}个任务",
        data=task_list,
        meta=meta
    )