#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 工作流引擎
自动化业务流程，实现智能化的项目流转和任务调度
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import Project, Task, User, ProjectStatusLog
from app.services.notification_service import NotificationService
from app.ai.service import get_ai_service
from app import StatusEnum, RoleEnum

class TriggerType(str, Enum):
    """触发器类型"""
    TIME_BASED = "time_based"      # 基于时间的触发器
    STATUS_CHANGE = "status_change" # 状态变更触发器
    DATA_CONDITION = "data_condition" # 数据条件触发器
    MANUAL = "manual"              # 手动触发

class ActionType(str, Enum):
    """动作类型"""
    SEND_NOTIFICATION = "send_notification"
    UPDATE_STATUS = "update_status"
    CREATE_TASK = "create_task"
    ASSIGN_USER = "assign_user"
    RUN_AI_ANALYSIS = "run_ai_analysis"
    CUSTOM_FUNCTION = "custom_function"

@dataclass
class WorkflowRule:
    """工作流规则"""
    id: str
    name: str
    description: str
    trigger_type: TriggerType
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    is_active: bool = True
    priority: int = 1

@dataclass
class WorkflowContext:
    """工作流上下文"""
    trigger_data: Dict[str, Any]
    project: Optional[Project] = None
    task: Optional[Task] = None
    user: Optional[User] = None
    timestamp: datetime = None

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
        self.ai_service = get_ai_service()
        
        # 注册的工作流规则
        self.rules: List[WorkflowRule] = []
        
        # 动作处理器
        self.action_handlers: Dict[ActionType, Callable] = {
            ActionType.SEND_NOTIFICATION: self._handle_send_notification,
            ActionType.UPDATE_STATUS: self._handle_update_status,
            ActionType.CREATE_TASK: self._handle_create_task,
            ActionType.ASSIGN_USER: self._handle_assign_user,
            ActionType.RUN_AI_ANALYSIS: self._handle_run_ai_analysis,
            ActionType.CUSTOM_FUNCTION: self._handle_custom_function
        }
        
        # 初始化默认规则
        self._init_default_rules()
    
    def register_rule(self, rule: WorkflowRule):
        """注册工作流规则"""
        self.rules.append(rule)
        print(f"✅ 注册工作流规则: {rule.name}")
    
    async def trigger_workflow(
        self, 
        trigger_type: TriggerType, 
        trigger_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """触发工作流"""
        
        results = []
        context = WorkflowContext(
            trigger_data=trigger_data,
            timestamp=datetime.utcnow()
        )
        
        # 查找匹配的规则
        matching_rules = self._find_matching_rules(trigger_type, trigger_data)
        
        # 按优先级排序执行
        matching_rules.sort(key=lambda x: x.priority, reverse=True)
        
        for rule in matching_rules:
            try:
                result = await self._execute_rule(rule, context)
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                print(f"❌ 工作流规则执行失败 {rule.name}: {e}")
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def process_scheduled_workflows(self):
        """处理定时工作流"""
        print("🔄 开始处理定时工作流...")
        
        # 处理截止日期提醒
        await self._process_deadline_reminders()
        
        # 处理逾期项目警告
        await self._process_overdue_alerts()
        
        # 处理收款提醒
        await self._process_payment_reminders()
        
        # 处理项目状态检查
        await self._process_status_health_check()
        
        # 处理自动任务创建
        await self._process_auto_task_creation()
        
        print("✅ 定时工作流处理完成")
    
    async def process_project_status_change(
        self, 
        project: Project, 
        old_status: str, 
        new_status: str, 
        operator: User
    ):
        """处理项目状态变更工作流"""
        
        trigger_data = {
            "project_id": project.id,
            "old_status": old_status,
            "new_status": new_status,
            "operator_id": operator.id
        }
        
        await self.trigger_workflow(TriggerType.STATUS_CHANGE, trigger_data)
    
    # 私有方法
    def _init_default_rules(self):
        """初始化默认工作流规则"""
        
        # 规则1: 项目创建后自动分配设计师
        self.register_rule(WorkflowRule(
            id="auto_assign_designer",
            name="自动分配设计师",
            description="项目创建后，如果未指定设计师，自动分配工作量最少的设计师",
            trigger_type=TriggerType.STATUS_CHANGE,
            trigger_conditions={
                "new_status": StatusEnum.PENDING_QUOTE,
                "designer_not_assigned": True
            },
            actions=[
                {
                    "type": ActionType.ASSIGN_USER,
                    "role": RoleEnum.DESIGNER,
                    "strategy": "least_workload"
                },
                {
                    "type": ActionType.SEND_NOTIFICATION,
                    "template": "project_assigned",
                    "recipients": ["assigned_designer"]
                }
            ]
        ))
        
        # 规则2: 项目进入设计阶段时创建设计任务
        self.register_rule(WorkflowRule(
            id="create_design_tasks",
            name="创建设计任务",
            description="项目状态变更为'设计中'时，自动创建设计相关任务",
            trigger_type=TriggerType.STATUS_CHANGE,
            trigger_conditions={
                "new_status": StatusEnum.IN_DESIGN
            },
            actions=[
                {
                    "type": ActionType.CREATE_TASK,
                    "task_template": "design_workflow"
                },
                {
                    "type": ActionType.RUN_AI_ANALYSIS,
                    "analysis_type": "design_requirements"
                }
            ]
        ))
        
        # 规则3: 项目逾期自动提醒
        self.register_rule(WorkflowRule(
            id="overdue_reminder",
            name="逾期项目提醒",
            description="每日检查逾期项目并发送提醒",
            trigger_type=TriggerType.TIME_BASED,
            trigger_conditions={
                "schedule": "daily",
                "time": "09:00"
            },
            actions=[
                {
                    "type": ActionType.CUSTOM_FUNCTION,
                    "function": "check_overdue_projects"
                }
            ]
        ))
        
        # 规则4: 收款状态自动更新
        self.register_rule(WorkflowRule(
            id="payment_status_update",
            name="收款状态自动更新",
            description="定金支付后自动进入设计阶段",
            trigger_type=TriggerType.STATUS_CHANGE,
            trigger_conditions={
                "new_status": StatusEnum.DEPOSIT_PAID
            },
            actions=[
                {
                    "type": ActionType.UPDATE_STATUS,
                    "target_status": StatusEnum.IN_DESIGN,
                    "delay_hours": 0
                },
                {
                    "type": ActionType.SEND_NOTIFICATION,
                    "template": "design_start",
                    "recipients": ["designer", "creator"]
                }
            ]
        ))
    
    def _find_matching_rules(
        self, 
        trigger_type: TriggerType, 
        trigger_data: Dict[str, Any]
    ) -> List[WorkflowRule]:
        """查找匹配的规则"""
        
        matching_rules = []
        
        for rule in self.rules:
            if not rule.is_active:
                continue
            
            if rule.trigger_type != trigger_type:
                continue
            
            # 检查触发条件
            if self._check_trigger_conditions(rule.trigger_conditions, trigger_data):
                matching_rules.append(rule)
        
        return matching_rules
    
    def _check_trigger_conditions(
        self, 
        conditions: Dict[str, Any], 
        trigger_data: Dict[str, Any]
    ) -> bool:
        """检查触发条件是否满足"""
        
        for key, expected_value in conditions.items():
            if key == "new_status":
                if trigger_data.get("new_status") != expected_value:
                    return False
            
            elif key == "old_status":
                if trigger_data.get("old_status") != expected_value:
                    return False
            
            elif key == "designer_not_assigned":
                if expected_value:
                    project_id = trigger_data.get("project_id")
                    if project_id:
                        project = self.db.query(Project).filter(Project.id == project_id).first()
                        if project and project.designer_id:
                            return False
            
            # 更多条件检查可以在这里添加
        
        return True
    
    async def _execute_rule(self, rule: WorkflowRule, context: WorkflowContext) -> Dict[str, Any]:
        """执行工作流规则"""
        
        results = []
        
        for action in rule.actions:
            action_type = ActionType(action["type"])
            handler = self.action_handlers.get(action_type)
            
            if handler:
                try:
                    result = await handler(action, context)
                    results.append(result)
                except Exception as e:
                    print(f"❌ 动作执行失败 {action_type}: {e}")
                    results.append({"error": str(e)})
        
        return {"actions_executed": len(results), "results": results}
    
    async def _handle_send_notification(
        self, 
        action: Dict[str, Any], 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """处理发送通知动作"""
        
        template = action.get("template")
        recipients = action.get("recipients", [])
        
        # 根据收件人类型确定具体用户
        target_users = []
        
        for recipient_type in recipients:
            if recipient_type == "assigned_designer":
                if context.project and context.project.designer_id:
                    designer = self.db.query(User).filter(User.id == context.project.designer_id).first()
                    if designer:
                        target_users.append(designer)
            
            elif recipient_type == "creator":
                if context.project and context.project.creator_id:
                    creator = self.db.query(User).filter(User.id == context.project.creator_id).first()
                    if creator:
                        target_users.append(creator)
            
            elif recipient_type == "designer":
                if context.project and context.project.designer_id:
                    designer = self.db.query(User).filter(User.id == context.project.designer_id).first()
                    if designer:
                        target_users.append(designer)
        
        # 发送通知
        notification_count = 0
        for user in target_users:
            if user.wechat_userid:
                # 这里应该调用通知服务
                notification_count += 1
        
        return {
            "template": template,
            "notifications_sent": notification_count,
            "recipients": [u.username for u in target_users]
        }
    
    async def _handle_update_status(
        self, 
        action: Dict[str, Any], 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """处理状态更新动作"""
        
        if not context.project:
            return {"error": "No project in context"}
        
        target_status = action.get("target_status")
        delay_hours = action.get("delay_hours", 0)
        
        if delay_hours > 0:
            # 延迟执行 (实际项目中应该使用任务队列)
            await asyncio.sleep(delay_hours * 3600)
        
        old_status = context.project.status
        context.project.status = target_status
        context.project.updated_at = datetime.utcnow()
        
        # 记录状态变更日志
        status_log = ProjectStatusLog(
            project_id=context.project.id,
            user_id=0,  # 系统自动操作
            from_status=old_status,
            to_status=target_status,
            change_reason="工作流自动更新",
            created_at=datetime.utcnow()
        )
        self.db.add(status_log)
        self.db.commit()
        
        return {
            "old_status": old_status,
            "new_status": target_status,
            "project_id": context.project.id
        }
    
    async def _handle_create_task(
        self, 
        action: Dict[str, Any], 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """处理创建任务动作"""
        
        if not context.project:
            return {"error": "No project in context"}
        
        task_template = action.get("task_template")
        
        # 根据模板创建任务
        tasks_created = []
        
        if task_template == "design_workflow":
            design_tasks = [
                {"title": "需求分析", "description": "分析客户设计需求", "priority": "high"},
                {"title": "创意构思", "description": "进行创意设计构思", "priority": "normal"},
                {"title": "初稿设计", "description": "完成设计初稿", "priority": "normal"},
                {"title": "客户沟通", "description": "与客户沟通设计方案", "priority": "normal"}
            ]
            
            for task_data in design_tasks:
                task = Task(
                    title=task_data["title"],
                    description=task_data["description"],
                    project_id=context.project.id,
                    creator_id=0,  # 系统创建
                    assignee_id=context.project.designer_id,
                    status="pending",
                    priority=task_data["priority"],
                    created_at=datetime.utcnow()
                )
                self.db.add(task)
                tasks_created.append(task_data["title"])
        
        self.db.commit()
        
        return {
            "template": task_template,
            "tasks_created": len(tasks_created),
            "task_titles": tasks_created
        }
    
    async def _handle_assign_user(
        self, 
        action: Dict[str, Any], 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """处理用户分配动作"""
        
        if not context.project:
            return {"error": "No project in context"}
        
        role = action.get("role")
        strategy = action.get("strategy")
        
        if role == RoleEnum.DESIGNER and strategy == "least_workload":
            # 查找工作量最少的设计师
            designers = self.db.query(User).filter(User.role == RoleEnum.DESIGNER).all()
            
            if designers:
                # 计算每个设计师的工作量
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
                best_designer = next(d for d in designers if d.id == best_designer_id)
                
                # 分配设计师
                context.project.designer_id = best_designer.id
                context.project.updated_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "assigned_user_id": best_designer.id,
                    "assigned_user_name": best_designer.full_name or best_designer.username,
                    "workload": designer_workload[best_designer_id]
                }
        
        return {"error": "No suitable user found"}
    
    async def _handle_run_ai_analysis(
        self, 
        action: Dict[str, Any], 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """处理AI分析动作"""
        
        if not context.project:
            return {"error": "No project in context"}
        
        analysis_type = action.get("analysis_type")
        
        try:
            if analysis_type == "design_requirements":
                # 分析设计需求
                project_data = {
                    "project_name": context.project.project_name,
                    "customer_name": context.project.customer_name,
                    "description": context.project.description,
                    "category": context.project.category
                }
                
                analysis = await self.ai_service.analyze_project(project_data)
                
                return {
                    "analysis_type": analysis_type,
                    "analysis_result": analysis,
                    "success": True
                }
            
        except Exception as e:
            return {
                "analysis_type": analysis_type,
                "error": str(e),
                "success": False
            }
        
        return {"error": "Unknown analysis type"}
    
    async def _handle_custom_function(
        self, 
        action: Dict[str, Any], 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """处理自定义函数动作"""
        
        function_name = action.get("function")
        
        if function_name == "check_overdue_projects":
            await self.notification_service.send_overdue_alerts()
            return {"function": function_name, "executed": True}
        
        return {"error": f"Unknown function: {function_name}"}
    
    # 定时任务处理方法
    async def _process_deadline_reminders(self):
        """处理截止日期提醒"""
        await self.notification_service.send_deadline_warnings(days_ahead=3)
        await self.notification_service.send_deadline_warnings(days_ahead=1)
    
    async def _process_overdue_alerts(self):
        """处理逾期项目警告"""
        await self.notification_service.send_overdue_alerts()
    
    async def _process_payment_reminders(self):
        """处理收款提醒"""
        await self.notification_service.send_payment_reminders()
    
    async def _process_status_health_check(self):
        """处理项目状态健康检查"""
        # 检查长时间停留在某个状态的项目
        week_ago = datetime.now() - timedelta(days=7)
        
        stuck_projects = self.db.query(Project).filter(
            and_(
                Project.updated_at < week_ago,
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        ).all()
        
        for project in stuck_projects:
            days_stuck = (datetime.now() - project.updated_at).days
            
            # 通知相关人员
            stakeholders = await self.notification_service._get_project_stakeholders(project)
            
            message = f"""🚨 项目状态提醒

项目：{project.project_name}
当前状态：{project.status}
停留时间：{days_stuck}天

请检查项目进展，及时更新状态。"""
            
            for stakeholder in stakeholders:
                if stakeholder.wechat_userid:
                    await self.notification_service._send_wechat_message(
                        stakeholder.wechat_userid, message
                    )
    
    async def _process_auto_task_creation(self):
        """处理自动任务创建"""
        # 为新进入设计阶段但没有任务的项目创建任务
        design_projects_without_tasks = self.db.query(Project).filter(
            and_(
                Project.status == StatusEnum.IN_DESIGN,
                ~Project.tasks.any()
            )
        ).all()
        
        for project in design_projects_without_tasks:
            # 创建基础设计任务
            await self._handle_create_task(
                {"task_template": "design_workflow"},
                WorkflowContext(trigger_data={}, project=project)
            )


# 全局工作流引擎实例
_workflow_engine = None

def get_workflow_engine(db: Session) -> WorkflowEngine:
    """获取工作流引擎实例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine(db)
    return _workflow_engine