#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 供应商管理API
提供供应商的CRUD操作、评级管理、合作统计等功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db
from app.models import Supplier, Task, User
from app.schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse, 
    PaginatedResponse, PaginationMeta
)
from app.auth import get_current_active_user
from app.permissions import Permission, check_permission
from app.api import success_response, error_response, API_TAGS
from datetime import datetime

router = APIRouter(prefix="/suppliers", tags=[API_TAGS["suppliers"]])

# 🔍 供应商查询API
@router.get("/", response_model=PaginatedResponse)
async def get_suppliers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service_type: Optional[str] = Query(None, description="服务类型筛选"),
    rating_min: Optional[int] = Query(None, ge=1, le=10, description="最低评分"),
    is_preferred: Optional[bool] = Query(None, description="是否优选供应商"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取供应商列表"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有查看供应商的权限"
        )
    
    # 构建查询
    query = db.query(Supplier)
    
    # 服务类型筛选
    if service_type:
        query = query.filter(Supplier.service_type.ilike(f"%{service_type}%"))
    
    # 评分筛选
    if rating_min:
        query = query.filter(Supplier.rating >= rating_min)
    
    # 优选供应商筛选
    if is_preferred is not None:
        query = query.filter(Supplier.is_preferred == is_preferred)
    
    # 搜索筛选
    if search:
        search_filter = or_(
            Supplier.name.ilike(f"%{search}%"),
            Supplier.company_name.ilike(f"%{search}%"),
            Supplier.contact_person.ilike(f"%{search}%"),
            Supplier.business_scope.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # 获取总数
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    # 分页查询 - 优选供应商优先，然后按评分排序
    skip = (page - 1) * page_size
    suppliers = query.order_by(
        Supplier.is_preferred.desc(),
        Supplier.rating.desc(),
        Supplier.name.asc()
    ).offset(skip).limit(page_size).all()
    
    # 转换为响应格式
    supplier_list = []
    for supplier in suppliers:
        supplier_data = SupplierResponse.model_validate(supplier)
        supplier_list.append(supplier_data.model_dump())
    
    # 分页元数据
    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )
    
    return PaginatedResponse(
        success=True,
        message=f"获取供应商列表成功，共{total}个供应商",
        data=supplier_list,
        meta=meta
    )

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取供应商详情"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有查看供应商的权限"
        )
    
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    return success_response(
        data=SupplierResponse.model_validate(supplier).model_dump(),
        message="获取供应商详情成功"
    )

# 🆕 供应商创建API
@router.post("/", response_model=SupplierResponse)
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新供应商"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_CREATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有创建供应商的权限"
        )
    
    # 检查供应商名称是否已存在
    existing_supplier = db.query(Supplier).filter(
        Supplier.name == supplier_data.name
    ).first()
    
    if existing_supplier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="供应商名称已存在"
        )
    
    # 创建供应商
    db_supplier = Supplier(
        name=supplier_data.name,
        company_name=supplier_data.company_name,
        contact_person=supplier_data.contact_person,
        phone=supplier_data.phone,
        email=supplier_data.email,
        address=supplier_data.address,
        service_type=supplier_data.service_type,
        business_scope=supplier_data.business_scope,
        rating=supplier_data.rating,
        payment_terms=supplier_data.payment_terms,
        notes=supplier_data.notes,
        created_at=datetime.utcnow()
    )
    
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    
    return success_response(
        data=SupplierResponse.model_validate(db_supplier).model_dump(),
        message=f"供应商 {supplier_data.name} 创建成功"
    )

#✏️ 供应商更新API
@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新供应商信息"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_UPDATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有更新供应商的权限"
        )
    
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    # 检查名称唯一性（如果更新了名称）
    update_data = supplier_data.model_dump(exclude_unset=True)
    if 'name' in update_data:
        existing_supplier = db.query(Supplier).filter(
            and_(Supplier.name == update_data['name'], Supplier.id != supplier_id)
        ).first()
        
        if existing_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="供应商名称已存在"
            )
    
    # 更新字段
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    supplier.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(supplier)
    
    return success_response(
        data=SupplierResponse.model_validate(supplier).model_dump(),
        message="供应商信息更新成功"
    )

# ⭐ 供应商评级API
@router.patch("/{supplier_id}/rating")
async def update_supplier_rating(
    supplier_id: int,
    rating: int = Query(..., ge=1, le=10, description="评分(1-10)"),
    is_preferred: Optional[bool] = Query(None, description="是否设为优选"),
    notes: Optional[str] = Query(None, description="评级备注"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新供应商评级"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_UPDATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有更新供应商评级的权限"
        )
    
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    old_rating = supplier.rating
    old_preferred = supplier.is_preferred
    
    # 更新评级
    supplier.rating = rating
    if is_preferred is not None:
        supplier.is_preferred = is_preferred
    
    # 添加评级备注
    if notes:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        rating_note = f"[{timestamp}] 评级更新: {old_rating}→{rating}, 备注: {notes}"
        if supplier.notes:
            supplier.notes = f"{supplier.notes}\n{rating_note}"
        else:
            supplier.notes = rating_note
    
    supplier.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(supplier)
    
    return success_response(
        data=SupplierResponse.model_validate(supplier).model_dump(),
        message=f"供应商评级已从 {old_rating} 更新为 {rating}"
    )

# 🗑️ 供应商删除API
@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除供应商"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_DELETE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有删除供应商的权限"
        )
    
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    # 检查是否有关联任务
    task_count = db.query(Task).filter(Task.supplier_id == supplier_id).count()
    if task_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该供应商有 {task_count} 个关联任务，无法删除"
        )
    
    supplier_name = supplier.name
    
    # 删除供应商
    db.delete(supplier)
    db.commit()
    
    return success_response(message=f"供应商 '{supplier_name}' 已删除")

# 📊 供应商统计API
@router.get("/statistics/overview")
async def get_supplier_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取供应商统计概览"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有查看供应商统计的权限"
        )
    
    # 基础统计
    total_suppliers = db.query(func.count(Supplier.id)).scalar()
    preferred_suppliers = db.query(func.count(Supplier.id)).filter(
        Supplier.is_preferred == True
    ).scalar()
    
    # 按服务类型统计
    service_type_stats = db.query(
        Supplier.service_type,
        func.count(Supplier.id).label('count')
    ).filter(Supplier.service_type.isnot(None)).group_by(Supplier.service_type).all()
    
    # 按评分段统计
    rating_stats = db.query(
        func.case(
            (Supplier.rating >= 9, '优秀(9-10分)'),
            (Supplier.rating >= 7, '良好(7-8分)'),
            (Supplier.rating >= 5, '一般(5-6分)'),
            else_='较差(1-4分)'
        ).label('rating_range'),
        func.count(Supplier.id).label('count')
    ).group_by('rating_range').all()
    
    # 合作频次统计 (基于任务数量)
    cooperation_stats = db.query(
        Supplier.name,
        func.count(Task.id).label('task_count')
    ).outerjoin(Task, Task.supplier_id == Supplier.id).group_by(
        Supplier.id, Supplier.name
    ).order_by(func.count(Task.id).desc()).limit(10).all()
    
    return success_response(
        data={
            "total_suppliers": total_suppliers,
            "preferred_suppliers": preferred_suppliers,
            "service_type_distribution": dict(service_type_stats),
            "rating_distribution": dict(rating_stats),
            "top_cooperation_suppliers": [
                {"name": name, "task_count": count} 
                for name, count in cooperation_stats
            ],
            "average_rating": db.query(func.avg(Supplier.rating)).scalar() or 0
        },
        message="供应商统计信息获取成功"
    )

# 🔍 供应商搜索API
@router.get("/search/by-service")
async def search_suppliers_by_service(
    service_type: str = Query(..., description="服务类型关键词"),
    min_rating: int = Query(5, ge=1, le=10, description="最低评分"),
    preferred_only: bool = Query(False, description="仅显示优选供应商"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按服务类型搜索供应商"""
    
    # 权限检查
    if not check_permission(current_user, Permission.SUPPLIER_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有查看供应商的权限"
        )
    
    # 构建查询
    query = db.query(Supplier).filter(
        and_(
            Supplier.service_type.ilike(f"%{service_type}%"),
            Supplier.rating >= min_rating
        )
    )
    
    if preferred_only:
        query = query.filter(Supplier.is_preferred == True)
    
    suppliers = query.order_by(
        Supplier.rating.desc(),
        Supplier.is_preferred.desc()
    ).all()
    
    # 转换为响应格式
    supplier_list = []
    for supplier in suppliers:
        supplier_data = SupplierResponse.model_validate(supplier)
        supplier_list.append(supplier_data.model_dump())
    
    return success_response(
        data=supplier_list,
        message=f"找到 {len(supplier_list)} 个匹配的供应商"
    )