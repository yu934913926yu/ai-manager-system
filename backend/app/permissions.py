#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - RBAC权限控制系统
基于角色的访问控制，支持细粒度权限管理
"""

from typing import List, Set, Dict, Optional, Callable
from enum import Enum
from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.models import User, Project
from app import RoleEnum
from app.auth import get_current_user, get_current_active_user

class Permission(str, Enum):
    """权限枚举"""
    # 🏢 系统管理权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    
    # 👥 用户管理权限
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ASSIGN_ROLE = "user:assign_role"
    
    # 📊 项目管理权限
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_ASSIGN = "project:assign"
    PROJECT_STATUS_CHANGE = "project:status_change"
    PROJECT_FINANCIAL = "project:financial"
    
    # 📋 任务管理权限
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    
    # 🏢 供应商管理权限
    SUPPLIER_CREATE = "supplier:create"
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_UPDATE = "supplier:update"
    SUPPLIER_DELETE = "supplier:delete"
    
    # 📁 文件管理权限
    FILE_UPLOAD = "file:upload"
    FILE_READ = "file:read"
    FILE_DELETE = "file:delete"
    FILE_MANAGE = "file:manage"
    
    # 💰 财务管理权限
    FINANCIAL_READ = "financial:read"
    FINANCIAL_WRITE = "financial:write"
    FINANCIAL_CONFIRM = "financial:confirm"
    FINANCIAL_REPORT = "financial:report"
    
    # 🤖 AI服务权限
    AI_USE = "ai:use"
    AI_MANAGE = "ai:manage"
    AI_CONVERSATION_VIEW = "ai:conversation_view"
    
    # 📊 报告和统计权限
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"
    STATISTICS_VIEW = "statistics:view"

class PermissionLevel(str, Enum):
    """权限级别"""
    NONE = "none"       # 无权限
    READ = "read"       # 只读
    WRITE = "write"     # 读写
    ADMIN = "admin"     # 管理权限

# 🎭 角色权限映射
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    RoleEnum.ADMIN: {
        # 管理员拥有所有权限
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_MONITOR,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_ASSIGN_ROLE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_ASSIGN,
        Permission.PROJECT_STATUS_CHANGE,
        Permission.PROJECT_FINANCIAL,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_DELETE,
        Permission.TASK_ASSIGN,
        Permission.SUPPLIER_CREATE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_UPDATE,
        Permission.SUPPLIER_DELETE,
        Permission.FILE_UPLOAD,
        Permission.FILE_READ,
        Permission.FILE_DELETE,
        Permission.FILE_MANAGE,
        Permission.FINANCIAL_READ,
        Permission.FINANCIAL_WRITE,
        Permission.FINANCIAL_CONFIRM,
        Permission.FINANCIAL_REPORT,
        Permission.AI_USE,
        Permission.AI_MANAGE,
        Permission.AI_CONVERSATION_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.STATISTICS_VIEW,
    },
    
    RoleEnum.DESIGNER: {
        # 设计师权限
        Permission.USER_READ,  # 查看用户信息
        Permission.PROJECT_CREATE,  # 创建项目
        Permission.PROJECT_READ,   # 查看项目
        Permission.PROJECT_UPDATE, # 更新项目
        Permission.PROJECT_STATUS_CHANGE,  # 变更项目状态
        Permission.TASK_CREATE,    # 创建任务
        Permission.TASK_READ,      # 查看任务
        Permission.TASK_UPDATE,    # 更新任务
        Permission.SUPPLIER_READ,  # 查看供应商
        Permission.FILE_UPLOAD,    # 上传文件
        Permission.FILE_READ,      # 查看文件
        Permission.FILE_DELETE,    # 删除自己上传的文件
        Permission.AI_USE,         # 使用AI服务
        Permission.REPORT_VIEW,    # 查看报告
    },
    
    RoleEnum.FINANCE: {
        # 财务权限
        Permission.USER_READ,      # 查看用户信息
        Permission.PROJECT_READ,   # 查看项目
        Permission.PROJECT_FINANCIAL,  # 项目财务信息
        Permission.TASK_READ,      # 查看任务
        Permission.SUPPLIER_READ,  # 查看供应商
        Permission.FILE_READ,      # 查看文件
        Permission.FINANCIAL_READ, # 查看财务记录
        Permission.FINANCIAL_WRITE,    # 创建财务记录
        Permission.FINANCIAL_CONFIRM,  # 确认财务记录
        Permission.FINANCIAL_REPORT,   # 财务报告
        Permission.AI_USE,         # 使用AI服务
        Permission.REPORT_VIEW,    # 查看报告
        Permission.REPORT_EXPORT,  # 导出报告
        Permission.STATISTICS_VIEW,    # 查看统计
    },
    
    RoleEnum.SALES: {
        # 销售权限
        Permission.USER_READ,      # 查看用户信息
        Permission.PROJECT_CREATE, # 创建项目
        Permission.PROJECT_READ,   # 查看项目
        Permission.PROJECT_UPDATE, # 更新项目
        Permission.PROJECT_ASSIGN, # 分配项目
        Permission.TASK_READ,      # 查看任务
        Permission.SUPPLIER_READ,  # 查看供应商
        Permission.FILE_UPLOAD,    # 上传文件
        Permission.FILE_READ,      # 查看文件
        Permission.AI_USE,         # 使用AI服务
        Permission.REPORT_VIEW,    # 查看报告
    }
}

# 📋 资源权限规则
class ResourcePermission:
    """资源权限规则"""
    
    @staticmethod
    def can_access_project(user: User, project: Project) -> bool:
        """检查用户是否可以访问项目"""
        # 管理员可以访问所有项目
        if user.role == RoleEnum.ADMIN or user.is_admin:
            return True
        
        # 项目创建者可以访问
        if project.creator_id == user.id:
            return True
        
        # 项目负责人可以访问
        if project.designer_id == user.id:
            return True
        
        # 销售可以访问自己负责的项目
        if project.sales_id == user.id:
            return True
        
        # 财务可以查看所有项目的财务信息
        if user.role == RoleEnum.FINANCE:
            return True
        
        return False
    
    @staticmethod
    def can_modify_project(user: User, project: Project) -> bool:
        """检查用户是否可以修改项目"""
        # 管理员可以修改所有项目
        if user.role == RoleEnum.ADMIN or user.is_admin:
            return True
        
        # 项目创建者可以修改
        if project.creator_id == user.id:
            return True
        
        # 项目负责人可以修改
        if project.designer_id == user.id:
            return True
        
        return False
    
    @staticmethod
    def can_access_financial_data(user: User, project: Project) -> bool:
        """检查用户是否可以访问财务数据"""
        # 管理员和财务可以访问所有财务数据
        if user.role in [RoleEnum.ADMIN, RoleEnum.FINANCE] or user.is_admin:
            return True
        
        # 项目创建者可以访问自己项目的财务数据
        if project.creator_id == user.id:
            return True
        
        return False

class PermissionChecker:
    """权限检查器"""
    
    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """检查用户是否具有指定权限"""
        if not user or not user.is_active:
            return False
        
        # 超级管理员拥有所有权限
        if user.is_admin:
            return True
        
        # 检查角色权限
        user_permissions = self.role_permissions.get(user.role, set())
        return permission in user_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """检查用户是否具有任意一个权限"""
        return any(self.has_permission(user, perm) for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """检查用户是否具有所有权限"""
        return all(self.has_permission(user, perm) for perm in permissions)
    
    def get_user_permissions(self, user: User) -> Set[Permission]:
        """获取用户的所有权限"""
        if not user or not user.is_active:
            return set()
        
        if user.is_admin:
            return set(Permission)
        
        return self.role_permissions.get(user.role, set())

# 全局权限检查器实例
permission_checker = PermissionChecker()

# 🚪 FastAPI权限依赖 (推荐使用方式)
class PermissionDependency:
    """权限依赖类 - 用于FastAPI路由"""
    
    def __init__(self, permission: Permission):
        self.permission = permission
    
    def __call__(self, current_user: User = Depends(get_current_active_user)):
        if not permission_checker.has_permission(current_user, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.permission.value}"
            )
        return current_user

class RoleDependency:
    """角色依赖类 - 用于FastAPI路由"""
    
    def __init__(self, role: str):
        self.role = role
    
    def __call__(self, current_user: User = Depends(get_current_active_user)):
        if current_user.role != self.role and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {self.role}"
            )
        return current_user

class ResourcePermissionDependency:
    """资源权限依赖类"""
    
    def __init__(self, resource_type: str, action: str = "read"):
        self.resource_type = resource_type
        self.action = action
    
    def __call__(self, current_user: User = Depends(get_current_active_user)):
        # 这里可以根据具体的资源类型和操作进行权限检查
        return current_user

# 🎯 便捷权限检查函数
def check_permission(user: User, permission: Permission) -> bool:
    """检查用户权限"""
    return permission_checker.has_permission(user, permission)

def check_project_access(user: User, project: Project) -> bool:
    """检查项目访问权限"""
    return ResourcePermission.can_access_project(user, project)

def check_project_modify(user: User, project: Project) -> bool:
    """检查项目修改权限"""
    return ResourcePermission.can_modify_project(user, project)

def check_financial_access(user: User, project: Project) -> bool:
    """检查财务数据访问权限"""
    return ResourcePermission.can_access_financial_data(user, project)

def require_project_access(user: User, project: Project):
    """要求项目访问权限"""
    if not check_project_access(user, project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this project"
        )

def require_project_modify(user: User, project: Project):
    """要求项目修改权限"""
    if not check_project_modify(user, project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to modify this project"
        )

def require_financial_access(user: User, project: Project):
    """要求财务数据访问权限"""
    if not check_financial_access(user, project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to financial data"
        )

# 🛡️ 便捷权限装饰器工厂 (简化版本)
def RequirePermission(permission: Permission):
    """权限依赖工厂函数 - 推荐使用"""
    return PermissionDependency(permission)

def RequireRole(role: str):
    """角色依赖工厂函数 - 推荐使用"""
    return RoleDependency(role)

def RequireAnyPermission(permissions: List[Permission]):
    """多权限依赖工厂函数"""
    def permission_dependency(current_user: User = Depends(get_current_active_user)):
        if not permission_checker.has_any_permission(current_user, permissions):
            permission_list = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires any of {permission_list}"
            )
        return current_user
    return permission_dependency

def RequireAllPermissions(permissions: List[Permission]):
    """全权限依赖工厂函数"""
    def permission_dependency(current_user: User = Depends(get_current_active_user)):
        if not permission_checker.has_all_permissions(current_user, permissions):
            permission_list = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires all of {permission_list}"
            )
        return current_user
    return permission_dependency

# 📊 权限管理工具
class PermissionManager:
    """权限管理器"""
    
    @staticmethod
    def get_role_permissions(role: str) -> Set[Permission]:
        """获取角色的所有权限"""
        return ROLE_PERMISSIONS.get(role, set())
    
    @staticmethod
    def add_role_permission(role: str, permission: Permission):
        """为角色添加权限"""
        if role not in ROLE_PERMISSIONS:
            ROLE_PERMISSIONS[role] = set()
        ROLE_PERMISSIONS[role].add(permission)
    
    @staticmethod
    def remove_role_permission(role: str, permission: Permission):
        """从角色移除权限"""
        if role in ROLE_PERMISSIONS:
            ROLE_PERMISSIONS[role].discard(permission)
    
    @staticmethod
    def get_permission_matrix() -> Dict[str, List[str]]:
        """获取权限矩阵"""
        return {
            role: [perm.value for perm in permissions]
            for role, permissions in ROLE_PERMISSIONS.items()
        }
    
    @staticmethod
    def validate_permission_change(user: User, target_user: User, new_permissions: List[Permission]) -> bool:
        """验证权限变更是否合法"""
        # 只有管理员可以修改权限
        if user.role != RoleEnum.ADMIN and not user.is_admin:
            return False
        
        # 不能修改自己的权限
        if user.id == target_user.id:
            return False
        
        return True

# 📈 权限审计
class PermissionAudit:
    """权限审计"""
    
    @staticmethod
    def log_permission_check(user: User, permission: Permission, granted: bool, resource: str = None):
        """记录权限检查日志"""
        # 这里可以记录到数据库或日志文件
        print(f"AUDIT: User {user.username} ({user.role}) "
              f"{'GRANTED' if granted else 'DENIED'} permission {permission.value} "
              f"for resource {resource or 'system'}")
    
    @staticmethod
    def get_user_permission_history(user: User, days: int = 30) -> List[dict]:
        """获取用户权限历史"""
        # 这里应该从审计日志中查询
        return []

# 使用示例和说明
"""
使用示例:

1. 在FastAPI路由中使用权限依赖:

@router.get("/admin-only")
async def admin_endpoint(user: User = Depends(RequireRole(RoleEnum.ADMIN))):
    return {"message": "Admin access granted"}

@router.post("/create-project") 
async def create_project(user: User = Depends(RequirePermission(Permission.PROJECT_CREATE))):
    return {"message": "Project creation allowed"}

@router.get("/financial-data")
async def get_financial_data(user: User = Depends(RequireAnyPermission([
    Permission.FINANCIAL_READ, 
    Permission.PROJECT_FINANCIAL
]))):
    return {"message": "Financial access granted"}

2. 在业务逻辑中手动检查权限:

def some_business_function(user: User, project: Project):
    if not check_project_access(user, project):
        raise HTTPException(status_code=403, detail="No project access")
    
    # 继续业务逻辑
    pass

3. 检查用户所有权限:

user_permissions = permission_checker.get_user_permissions(user)
print(f"User {user.username} has permissions: {[p.value for p in user_permissions]}")
"""

# 🔍 测试函数
def test_permissions():
    """测试权限系统"""
    print("🛡️ AI管理系统权限测试")
    print("=" * 50)
    
    # 创建测试用户
    admin_user = User(id=1, username="admin", role=RoleEnum.ADMIN, is_admin=True, is_active=True)
    designer_user = User(id=2, username="designer", role=RoleEnum.DESIGNER, is_active=True)
    finance_user = User(id=3, username="finance", role=RoleEnum.FINANCE, is_active=True)
    
    # 测试权限检查
    test_cases = [
        (admin_user, Permission.SYSTEM_ADMIN, True),
        (designer_user, Permission.PROJECT_CREATE, True),
        (designer_user, Permission.SYSTEM_ADMIN, False),
        (finance_user, Permission.FINANCIAL_READ, True),
        (finance_user, Permission.PROJECT_DELETE, False),
    ]
    
    for user, permission, expected in test_cases:
        result = permission_checker.has_permission(user, permission)
        status = "✅" if result == expected else "❌"
        print(f"{status} {user.role} - {permission.value}: {result}")
    
    print("=" * 50)

if __name__ == "__main__":
    test_permissions()