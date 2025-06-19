#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 项目业务逻辑服务
核心项目管理业务逻辑，包括状态流转、智能分析等
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Project, User, Task, ProjectStatusLog, FinancialRecord
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.auth import get_current_user
from app.permissions import Permission, check_permission
from app.ai.service import get_ai_service
from app.services.notification_service import NotificationService
from app import StatusEnum, RoleEnum

class ProjectBusinessException(Exception):
    """项目业务异常"""
    pass

class ProjectService:
    """项目业务逻辑服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = get_ai_service()
        self.notification_service = NotificationService(db)
    
    def create_project_with_analysis(
        self, 
        project_data: ProjectCreate, 
        creator: User,
        auto_analyze: bool = True
    ) -> Dict[str, Any]:
        """创建项目并进行AI分析"""
        
        try:
            # 1. 创建项目
            project = self._create_project_record(project_data, creator)
            
            # 2. AI智能分析（可选）
            analysis_result = None
            if auto_analyze:
                try:
                    analysis_result = await self._perform_project_analysis(project)
                except Exception as e:
                    print(f"⚠️ AI分析失败，但项目创建成功: {e}")
            
            # 3. 自动分配设计师（如果有合适的）
            if not project.designer_id:
                suitable_designer = self._find_suitable_designer(project)
                if suitable_designer:
                    project.designer_id = suitable_designer.id
                    self.db.commit()
            
            # 4. 发送通知
            await self._send_project_creation_notifications(project, creator)
            
            # 5. 创建初始任务
            initial_tasks = self._create_initial_tasks(project)
            
            return {
                "success": True,
                "project": project,
                "analysis": analysis_result,
                "auto_assigned_designer": bool(project.designer_id),
                "initial_tasks_count": len(initial_tasks)
            }
            
        except Exception as e:
            self.db.rollback()
            raise ProjectBusinessException(f"项目创建失败: {str(e)}")
    
    def smart_status_transition(
        self, 
        project_id: int, 
        new_status: str, 
        operator: User,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """智能状态流转"""
        
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ProjectBusinessException("项目不存在")
        
        old_status = project.status
        
        # 1. 验证状态流转的合法性
        self._validate_status_transition(old_status, new_status, operator)
        
        # 2. 执行状态变更
        project.status = new_status
        project.updated_at = datetime.utcnow()
        
        # 3. 状态相关的自动操作
        status_effects = self._handle_status_side_effects(project, old_status, new_status)
        
        # 4. 记录状态变更日志
        self._log_status_change(project, old_status, new_status, operator, notes)
        
        # 5. 发送相关通知
        await self._send_status_change_notifications(project, old_status, new_status, operator)
        
        self.db.commit()
        
        return {
            "success": True,
            "old_status": old_status,
            "new_status": new_status,
            "side_effects": status_effects,
            "next_actions": self._get_next_recommended_actions(project)
        }
    
    def calculate_project_profitability(self, project_id: int) -> Dict[str, Any]:
        """计算项目盈利能力"""
        
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ProjectBusinessException("项目不存在")
        
        # 获取项目的所有财务记录
        income_records = self.db.query(FinancialRecord).filter(
            and_(
                FinancialRecord.project_id == project_id,
                FinancialRecord.record_type == "income"
            )
        ).all()
        
        expense_records = self.db.query(FinancialRecord).filter(
            and_(
                FinancialRecord.project_id == project_id,
                FinancialRecord.record_type == "expense"
            )
        ).all()
        
        # 计算收入和支出
        total_income = sum(record.amount for record in income_records)
        total_expense = sum(record.amount for record in expense_records)
        net_profit = total_income - total_expense
        
        # 计算利润率
        profit_margin = (net_profit / total_income * 100) if total_income > 0 else 0
        
        # 计算项目周期
        project_duration = None
        if project.started_at and project.completed_at:
            project_duration = (project.completed_at - project.started_at).days
        
        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "net_profit": float(net_profit),
            "profit_margin": round(profit_margin, 2),
            "project_duration_days": project_duration,
            "cost_breakdown": self._get_cost_breakdown(expense_records),
            "profitability_rating": self._rate_profitability(profit_margin)
        }
    
    def get_project_timeline(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目时间线"""
        
        # 获取状态变更记录
        status_logs = self.db.query(ProjectStatusLog).filter(
            ProjectStatusLog.project_id == project_id
        ).order_by(ProjectStatusLog.created_at.asc()).all()
        
        timeline = []
        for log in status_logs:
            user = self.db.query(User).filter(User.id == log.user_id).first()
            
            timeline.append({
                "timestamp": log.created_at,
                "event_type": "status_change",
                "from_status": log.from_status,
                "to_status": log.to_status,
                "operator": user.full_name or user.username if user else "未知用户",
                "notes": log.notes,
                "change_reason": log.change_reason
            })
        
        return timeline
    
    def get_overdue_projects(self, user: User = None) -> List[Dict[str, Any]]:
        """获取逾期项目"""
        
        today = date.today()
        query = self.db.query(Project).filter(
            and_(
                Project.deadline < today,
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        )
        
        # 如果指定用户，只查看相关项目
        if user and not check_permission(user, Permission.PROJECT_READ):
            query = query.filter(
                or_(
                    Project.creator_id == user.id,
                    Project.designer_id == user.id,
                    Project.sales_id == user.id
                )
            )
        
        overdue_projects = query.all()
        
        result = []
        for project in overdue_projects:
            overdue_days = (today - project.deadline).days
            
            result.append({
                "project_id": project.id,
                "project_number": project.project_number,
                "project_name": project.project_name,
                "customer_name": project.customer_name,
                "deadline": project.deadline,
                "overdue_days": overdue_days,
                "current_status": project.status,
                "urgency_level": self._calculate_urgency_level(overdue_days, project.quoted_price)
            })
        
        # 按紧急程度排序
        result.sort(key=lambda x: x["urgency_level"], reverse=True)
        return result
    
    def batch_update_projects(
        self, 
        updates: List[Dict[str, Any]], 
        operator: User
    ) -> Dict[str, Any]:
        """批量更新项目"""
        
        success_count = 0
        error_count = 0
        errors = []
        
        for update_data in updates:
            try:
                project_id = update_data.get("project_id")
                if not project_id:
                    continue
                
                project = self.db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    continue
                
                # 应用更新
                for field, value in update_data.items():
                    if field != "project_id" and hasattr(project, field):
                        setattr(project, field, value)
                
                project.updated_at = datetime.utcnow()
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append({
                    "project_id": update_data.get("project_id"),
                    "error": str(e)
                })
        
        self.db.commit()
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }
    
    # 私有方法
    def _create_project_record(self, project_data: ProjectCreate, creator: User) -> Project:
        """创建项目记录"""
        # 生成项目编号
        project_count = self.db.query(func.count(Project.id)).scalar()
        project_number = f"PRJ{datetime.now().strftime('%Y%m%d')}{project_count + 1:03d}"
        
        project = Project(
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
            creator_id=creator.id,
            status=StatusEnum.PENDING_QUOTE,
            created_at=datetime.utcnow()
        )
        
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        return project
    
    async def _perform_project_analysis(self, project: Project) -> Dict[str, Any]:
        """执行项目AI分析"""
        project_data = {
            "project_name": project.project_name,
            "customer_name": project.customer_name,
            "category": project.category,
            "quoted_price": float(project.quoted_price) if project.quoted_price else None,
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "description": project.description
        }
        
        return await self.ai_service.analyze_project(project_data)
    
    def _find_suitable_designer(self, project: Project) -> Optional[User]:
        """寻找合适的设计师"""
        # 查找可用的设计师（简单实现：工作量最少的设计师）
        designers = self.db.query(User).filter(User.role == RoleEnum.DESIGNER).all()
        
        if not designers:
            return None
        
        # 计算每个设计师的当前工作量
        designer_workload = {}
        for designer in designers:
            active_projects = self.db.query(Project).filter(
                and_(
                    Project.designer_id == designer.id,
                    Project.status.in_([StatusEnum.IN_DESIGN, StatusEnum.PENDING_APPROVAL])
                )
            ).count()
            designer_workload[designer.id] = active_projects
        
        # 选择工作量最少的设计师
        best_designer_id = min(designer_workload.keys(), key=lambda x: designer_workload[x])
        return next(d for d in designers if d.id == best_designer_id)
    
    def _validate_status_transition(self, old_status: str, new_status: str, operator: User):
        """验证状态流转合法性"""
        # 定义状态流转规则
        valid_transitions = {
            StatusEnum.PENDING_QUOTE: [StatusEnum.QUOTED, StatusEnum.ARCHIVED],
            StatusEnum.QUOTED: [StatusEnum.CONFIRMED, StatusEnum.PENDING_QUOTE],
            StatusEnum.CONFIRMED: [StatusEnum.DEPOSIT_PAID, StatusEnum.QUOTED],
            StatusEnum.DEPOSIT_PAID: [StatusEnum.IN_DESIGN],
            StatusEnum.IN_DESIGN: [StatusEnum.PENDING_APPROVAL],
            StatusEnum.PENDING_APPROVAL: [StatusEnum.APPROVED, StatusEnum.IN_DESIGN],
            StatusEnum.APPROVED: [StatusEnum.IN_PRODUCTION],
            StatusEnum.IN_PRODUCTION: [StatusEnum.COMPLETED],
            StatusEnum.COMPLETED: [StatusEnum.PAID, StatusEnum.ARCHIVED],
            StatusEnum.PAID: [StatusEnum.ARCHIVED]
        }
        
        if new_status not in valid_transitions.get(old_status, []):
            # 管理员可以进行任意状态变更
            if not (operator.is_admin or operator.role == RoleEnum.ADMIN):
                raise ProjectBusinessException(f"不允许从 {old_status} 直接变更为 {new_status}")
    
    def _handle_status_side_effects(self, project: Project, old_status: str, new_status: str) -> List[str]:
        """处理状态变更的副作用"""
        effects = []
        
        if new_status == StatusEnum.IN_DESIGN and not project.started_at:
            project.started_at = datetime.utcnow()
            effects.append("设置项目开始时间")
        
        if new_status == StatusEnum.COMPLETED and not project.completed_at:
            project.completed_at = datetime.utcnow()
            effects.append("设置项目完成时间")
        
        if new_status == StatusEnum.DEPOSIT_PAID:
            project.deposit_paid = True
            effects.append("标记定金已付")
        
        if new_status == StatusEnum.PAID:
            project.final_paid = True
            effects.append("标记尾款已付")
        
        return effects
    
    def _log_status_change(
        self, 
        project: Project, 
        old_status: str, 
        new_status: str, 
        operator: User, 
        notes: Optional[str]
    ):
        """记录状态变更日志"""
        status_log = ProjectStatusLog(
            project_id=project.id,
            user_id=operator.id,
            from_status=old_status,
            to_status=new_status,
            change_reason="状态流转",
            notes=notes,
            created_at=datetime.utcnow()
        )
        self.db.add(status_log)
    
    async def _send_project_creation_notifications(self, project: Project, creator: User):
        """发送项目创建通知"""
        # 通知设计师
        if project.designer_id and project.designer_id != creator.id:
            await self.notification_service.send_project_assignment_notification(
                project, creator
            )
    
    async def _send_status_change_notifications(
        self, 
        project: Project, 
        old_status: str, 
        new_status: str, 
        operator: User
    ):
        """发送状态变更通知"""
        await self.notification_service.send_status_change_notification(
            project, old_status, new_status, operator
        )
    
    def _create_initial_tasks(self, project: Project) -> List[Task]:
        """创建初始任务"""
        initial_tasks = []
        
        # 根据项目类型创建不同的初始任务
        if project.category == "LOGO设计":
            task_templates = [
                {"title": "需求沟通", "description": "与客户详细沟通设计需求"},
                {"title": "创意构思", "description": "进行LOGO创意设计构思"},
                {"title": "初稿设计", "description": "完成LOGO初稿设计"}
            ]
        else:
            task_templates = [
                {"title": "项目启动", "description": "项目启动和需求确认"},
                {"title": "设计执行", "description": "按需求执行设计工作"}
            ]
        
        for i, template in enumerate(task_templates):
            task = Task(
                title=template["title"],
                description=template["description"],
                project_id=project.id,
                creator_id=project.creator_id,
                assignee_id=project.designer_id,
                status="pending",
                priority="normal",
                created_at=datetime.utcnow()
            )
            self.db.add(task)
            initial_tasks.append(task)
        
        self.db.commit()
        return initial_tasks
    
    def _get_next_recommended_actions(self, project: Project) -> List[str]:
        """获取下一步推荐操作"""
        actions = []
        
        if project.status == StatusEnum.PENDING_QUOTE:
            actions.append("制定项目报价")
            actions.append("发送报价给客户")
        
        elif project.status == StatusEnum.QUOTED:
            actions.append("跟进客户确认")
            actions.append("准备合同文件")
        
        elif project.status == StatusEnum.CONFIRMED:
            actions.append("发送收款信息给客户")
            actions.append("准备项目启动")
        
        elif project.status == StatusEnum.DEPOSIT_PAID:
            actions.append("通知设计师开始工作")
            actions.append("建立项目沟通群")
        
        elif project.status == StatusEnum.IN_DESIGN:
            actions.append("定期检查设计进度")
            actions.append("准备中期汇报")
        
        elif project.status == StatusEnum.PENDING_APPROVAL:
            actions.append("联系客户确认设计稿")
            actions.append("准备修改意见收集")
        
        elif project.status == StatusEnum.APPROVED:
            actions.append("联系供应商开始生产")
            actions.append("监控生产进度")
        
        elif project.status == StatusEnum.IN_PRODUCTION:
            actions.append("跟进生产质量")
            actions.append("准备交付验收")
        
        elif project.status == StatusEnum.COMPLETED:
            actions.append("安排项目交付")
            actions.append("发送尾款账单")
        
        return actions
    
    def _get_cost_breakdown(self, expense_records: List[FinancialRecord]) -> Dict[str, float]:
        """获取成本分解"""
        breakdown = {}
        for record in expense_records:
            category = record.category or "其他"
            breakdown[category] = breakdown.get(category, 0) + float(record.amount)
        
        return breakdown
    
    def _rate_profitability(self, profit_margin: float) -> str:
        """评级盈利能力"""
        if profit_margin >= 50:
            return "优秀"
        elif profit_margin >= 30:
            return "良好"
        elif profit_margin >= 10:
            return "一般"
        elif profit_margin >= 0:
            return "微利"
        else:
            return "亏损"
    
    def _calculate_urgency_level(self, overdue_days: int, project_amount: Optional[Decimal]) -> int:
        """计算紧急程度"""
        urgency = overdue_days  # 基础紧急度
        
        # 金额越大，紧急度越高
        if project_amount:
            if project_amount >= 50000:
                urgency += 10
            elif project_amount >= 10000:
                urgency += 5
            elif project_amount >= 5000:
                urgency += 2
        
        return urgency