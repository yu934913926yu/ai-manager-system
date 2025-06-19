#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 自动提醒引擎
智能分析项目状态，主动发送各类提醒通知
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db_context
from app.models import Project, Task, User, AIConversation, FinancialRecord
from app.services.notification_service import NotificationService
from app.ai.service import get_ai_service
from app import StatusEnum, RoleEnum

class ReminderEngine:
    """自动提醒引擎"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        
        # 提醒规则配置
        self.reminder_rules = {
            "deadline_warning_days": [7, 3, 1],  # 截止日期前N天提醒
            "status_stuck_days": 5,              # 状态停留N天算卡住
            "payment_overdue_days": 3,           # 付款逾期N天提醒
            "no_activity_days": 7,               # N天无活动算异常
            "urgent_response_hours": 2           # 紧急事项N小时内需响应
        }
        
        print("✅ 自动提醒引擎初始化完成")
    
    async def send_daily_reminders(self):
        """发送每日提醒汇总"""
        print("📬 开始发送每日提醒...")
        
        with get_db_context() as db:
            notification_service = NotificationService(db)
            
            # 1. 截止日期提醒
            await self._send_deadline_reminders(db, notification_service)
            
            # 2. 卡住状态提醒
            await self._send_stuck_status_reminders(db, notification_service)
            
            # 3. 收款提醒
            await self._send_payment_reminders(db, notification_service)
            
            # 4. 逾期项目提醒
            await self._send_overdue_reminders(db, notification_service)
            
            # 5. 个人工作汇总
            await self._send_personal_summaries(db, notification_service)
        
        print("✅ 每日提醒发送完成")
    
    async def check_urgent_items(self):
        """检查紧急事项"""
        print("🚨 检查紧急事项...")
        
        with get_db_context() as db:
            notification_service = NotificationService(db)
            
            # 1. 今日到期项目
            today_due_projects = db.query(Project).filter(
                and_(
                    Project.deadline == date.today(),
                    Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
                )
            ).all()
            
            for project in today_due_projects:
                await self._send_urgent_deadline_alert(project, db, notification_service)
            
            # 2. 逾期未回复的重要消息
            await self._check_unresponded_messages(db, notification_service)
            
            # 3. 系统异常项目
            await self._check_abnormal_projects(db, notification_service)
        
        print("✅ 紧急事项检查完成")
    
    async def send_project_milestone_reminder(self, project_id: int, milestone: str):
        """发送项目里程碑提醒"""
        with get_db_context() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return
            
            notification_service = NotificationService(db)
            
            # 生成个性化提醒
            try:
                reminder_text = await self.ai_service.generate_reminder_text(
                    "milestone_reached",
                    {
                        "project_name": project.project_name,
                        "customer_name": project.customer_name,
                        "milestone": milestone,
                        "project_status": project.status
                    }
                )
            except Exception:
                reminder_text = f"项目 {project.project_name} 已达到里程碑: {milestone}"
            
            # 通知相关人员
            stakeholders = await notification_service._get_project_stakeholders(project)
            for stakeholder in stakeholders:
                if stakeholder.wechat_userid:
                    await notification_service._send_wechat_message(
                        stakeholder.wechat_userid, 
                        reminder_text
                    )
    
    async def schedule_custom_reminder(
        self, 
        user_id: int, 
        message: str, 
        remind_at: datetime,
        related_project_id: Optional[int] = None
    ):
        """安排自定义提醒"""
        from app.tasks.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        
        # 创建一次性任务
        job_id = f"custom_reminder_{user_id}_{int(remind_at.timestamp())}"
        
        scheduler.add_one_time_job(
            func=self._send_custom_reminder,
            job_id=job_id,
            run_date=remind_at,
            args=[user_id, message, related_project_id]
        )
        
        print(f"⏰ 已安排自定义提醒: {job_id}")
    
    # 私有方法
    async def _send_deadline_reminders(self, db: Session, notification_service: NotificationService):
        """发送截止日期提醒"""
        for days in self.reminder_rules["deadline_warning_days"]:
            warning_date = date.today() + timedelta(days=days)
            
            upcoming_projects = db.query(Project).filter(
                and_(
                    Project.deadline == warning_date,
                    Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
                )
            ).all()
            
            for project in upcoming_projects:
                try:
                    reminder_text = await self.ai_service.generate_reminder_text(
                        "deadline_warning",
                        {
                            "project_name": project.project_name,
                            "customer_name": project.customer_name,
                            "deadline": project.deadline.strftime('%Y-%m-%d'),
                            "remaining_days": days,
                            "current_status": project.status
                        }
                    )
                    
                    # 通知项目相关人员
                    stakeholders = await notification_service._get_project_stakeholders(project)
                    for stakeholder in stakeholders:
                        if stakeholder.wechat_userid:
                            await notification_service._send_wechat_message(
                                stakeholder.wechat_userid, 
                                reminder_text
                            )
                    
                    print(f"📅 发送截止提醒: {project.project_name} ({days}天后到期)")
                    
                except Exception as e:
                    print(f"❌ 发送截止提醒失败 {project.project_name}: {e}")
    
    async def _send_stuck_status_reminders(self, db: Session, notification_service: NotificationService):
        """发送状态卡住提醒"""
        stuck_date = datetime.now() - timedelta(days=self.reminder_rules["status_stuck_days"])
        
        stuck_projects = db.query(Project).filter(
            and_(
                Project.updated_at < stuck_date,
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        ).all()
        
        for project in stuck_projects:
            days_stuck = (datetime.now() - project.updated_at).days
            
            try:
                reminder_text = await self.ai_service.generate_reminder_text(
                    "status_stuck",
                    {
                        "project_name": project.project_name,
                        "current_status": project.status,
                        "stuck_days": days_stuck
                    }
                )
                
                # 通知项目负责人和管理员
                stakeholders = await notification_service._get_project_stakeholders(project)
                admins = db.query(User).filter(
                    or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
                ).all()
                
                all_recipients = list(set(stakeholders + admins))
                
                for recipient in all_recipients:
                    if recipient.wechat_userid:
                        await notification_service._send_wechat_message(
                            recipient.wechat_userid, 
                            reminder_text
                        )
                
                print(f"⚠️ 发送状态卡住提醒: {project.project_name} (卡住{days_stuck}天)")
                
            except Exception as e:
                print(f"❌ 发送状态卡住提醒失败 {project.project_name}: {e}")
    
    async def _send_payment_reminders(self, db: Session, notification_service: NotificationService):
        """发送收款提醒"""
        # 定金提醒
        deposit_projects = db.query(Project).filter(
            and_(
                Project.status == StatusEnum.CONFIRMED,
                Project.deposit_paid == False
            )
        ).all()
        
        # 尾款提醒
        final_payment_projects = db.query(Project).filter(
            and_(
                Project.status == StatusEnum.COMPLETED,
                Project.final_paid == False
            )
        ).all()
        
        # 处理定金提醒
        for project in deposit_projects:
            await self._send_single_payment_reminder(
                project, "定金", db, notification_service
            )
        
        # 处理尾款提醒
        for project in final_payment_projects:
            await self._send_single_payment_reminder(
                project, "尾款", db, notification_service
            )
    
    async def _send_single_payment_reminder(
        self, 
        project: Project, 
        payment_type: str, 
        db: Session, 
        notification_service: NotificationService
    ):
        """发送单个收款提醒"""
        try:
            amount = project.deposit_amount if payment_type == "定金" else project.final_price
            
            reminder_text = await self.ai_service.generate_reminder_text(
                "payment_reminder",
                {
                    "project_name": project.project_name,
                    "customer_name": project.customer_name,
                    "amount": amount or "未设定",
                    "payment_type": payment_type
                }
            )
            
            # 通知财务和管理员
            finance_users = db.query(User).filter(User.role == RoleEnum.FINANCE).all()
            admins = db.query(User).filter(
                or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
            ).all()
            
            recipients = finance_users + admins
            
            for recipient in recipients:
                if recipient.wechat_userid:
                    await notification_service._send_wechat_message(
                        recipient.wechat_userid, 
                        reminder_text
                    )
            
            print(f"💰 发送{payment_type}提醒: {project.project_name}")
            
        except Exception as e:
            print(f"❌ 发送{payment_type}提醒失败 {project.project_name}: {e}")
    
    async def _send_overdue_reminders(self, db: Session, notification_service: NotificationService):
        """发送逾期项目提醒"""
        today = date.today()
        
        overdue_projects = db.query(Project).filter(
            and_(
                Project.deadline < today,
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        ).all()
        
        for project in overdue_projects:
            overdue_days = (today - project.deadline).days
            
            try:
                reminder_text = await self.ai_service.generate_reminder_text(
                    "project_overdue",
                    {
                        "project_name": project.project_name,
                        "customer_name": project.customer_name,
                        "overdue_days": overdue_days,
                        "current_status": project.status
                    }
                )
                
                # 通知项目负责人和管理员
                stakeholders = await notification_service._get_project_stakeholders(project)
                admins = db.query(User).filter(
                    or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
                ).all()
                
                all_recipients = list(set(stakeholders + admins))
                
                for recipient in all_recipients:
                    if recipient.wechat_userid:
                        await notification_service._send_wechat_message(
                            recipient.wechat_userid, 
                            reminder_text
                        )
                
                print(f"🚨 发送逾期提醒: {project.project_name} (逾期{overdue_days}天)")
                
            except Exception as e:
                print(f"❌ 发送逾期提醒失败 {project.project_name}: {e}")
    
    async def _send_personal_summaries(self, db: Session, notification_service: NotificationService):
        """发送个人工作汇总"""
        active_users = db.query(User).filter(User.is_active == True).all()
        
        for user in active_users:
            if not user.wechat_userid:
                continue
            
            try:
                # 获取用户今日相关任务
                today = date.today()
                
                # 今日到期任务
                due_tasks = db.query(Task).filter(
                    and_(
                        Task.assignee_id == user.id,
                        Task.due_date == today,
                        Task.status != "completed"
                    )
                ).all()
                
                # 用户负责的进行中项目
                active_projects = db.query(Project).filter(
                    and_(
                        or_(
                            Project.creator_id == user.id,
                            Project.designer_id == user.id,
                            Project.sales_id == user.id
                        ),
                        Project.status.in_([
                            StatusEnum.IN_DESIGN, 
                            StatusEnum.PENDING_APPROVAL,
                            StatusEnum.IN_PRODUCTION
                        ])
                    )
                ).all()
                
                # 生成个人汇总
                if due_tasks or active_projects:
                    summary = await self._generate_personal_summary(
                        user, due_tasks, active_projects
                    )
                    
                    await notification_service._send_wechat_message(
                        user.wechat_userid, 
                        summary
                    )
                    
                    print(f"📊 发送个人汇总: {user.username}")
                
            except Exception as e:
                print(f"❌ 发送个人汇总失败 {user.username}: {e}")
    
    async def _generate_personal_summary(
        self, 
        user: User, 
        due_tasks: List[Task], 
        active_projects: List[Project]
    ) -> str:
        """生成个人工作汇总"""
        summary = f"📊 {user.full_name or user.username} 今日工作提醒\n\n"
        
        if due_tasks:
            summary += f"📌 今日到期任务 ({len(due_tasks)}个)：\n"
            for task in due_tasks[:3]:  # 只显示前3个
                summary += f"• {task.title}\n"
            if len(due_tasks) > 3:
                summary += f"• ...还有{len(due_tasks)-3}个任务\n"
            summary += "\n"
        
        if active_projects:
            summary += f"🔄 进行中项目 ({len(active_projects)}个)：\n"
            for project in active_projects[:3]:  # 只显示前3个
                summary += f"• {project.project_name} ({project.status})\n"
            if len(active_projects) > 3:
                summary += f"• ...还有{len(active_projects)-3}个项目\n"
        
        if not due_tasks and not active_projects:
            summary += "✅ 今日无特别紧急的任务和项目\n祝您工作愉快！"
        else:
            summary += "\n💡 详情请查看Web管理界面或询问AI总管"
        
        return summary
    
    async def _send_urgent_deadline_alert(
        self, 
        project: Project, 
        db: Session, 
        notification_service: NotificationService
    ):
        """发送紧急截止警告"""
        alert_text = f"""🚨 紧急提醒！

项目：{project.project_name}
客户：{project.customer_name}
状态：{project.status}

⏰ 今日即将到期！请立即处理！

如需帮助，请及时沟通。"""
        
        # 通知所有相关人员
        stakeholders = await notification_service._get_project_stakeholders(project)
        admins = db.query(User).filter(
            or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
        ).all()
        
        all_recipients = list(set(stakeholders + admins))
        
        for recipient in all_recipients:
            if recipient.wechat_userid:
                await notification_service._send_wechat_message(
                    recipient.wechat_userid, 
                    alert_text
                )
    
    async def _check_unresponded_messages(self, db: Session, notification_service: NotificationService):
        """检查未回复的重要消息"""
        # 检查最近2小时内的AI对话，看是否有需要人工处理的情况
        two_hours_ago = datetime.now() - timedelta(hours=2)
        
        recent_conversations = db.query(AIConversation).filter(
            and_(
                AIConversation.created_at >= two_hours_ago,
                AIConversation.ai_response.like("%请联系%")  # 包含"请联系"的回复可能需要人工处理
            )
        ).all()
        
        if recent_conversations:
            # 通知管理员
            admins = db.query(User).filter(
                or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
            ).all()
            
            alert_text = f"🔔 系统提醒\n\n最近2小时内有 {len(recent_conversations)} 条可能需要人工处理的AI对话，请及时查看。"
            
            for admin in admins:
                if admin.wechat_userid:
                    await notification_service._send_wechat_message(
                        admin.wechat_userid, 
                        alert_text
                    )
    
    async def _check_abnormal_projects(self, db: Session, notification_service: NotificationService):
        """检查异常项目"""
        # 检查数据异常的项目
        abnormal_projects = []
        
        # 1. 报价为空的非初始状态项目
        no_price_projects = db.query(Project).filter(
            and_(
                Project.quoted_price.is_(None),
                Project.status != StatusEnum.PENDING_QUOTE
            )
        ).all()
        
        abnormal_projects.extend([(p, "缺少报价信息") for p in no_price_projects])
        
        # 2. 没有负责人的进行中项目
        no_designer_projects = db.query(Project).filter(
            and_(
                Project.designer_id.is_(None),
                Project.status.in_([StatusEnum.IN_DESIGN, StatusEnum.PENDING_APPROVAL])
            )
        ).all()
        
        abnormal_projects.extend([(p, "缺少设计师分配") for p in no_designer_projects])
        
        # 发送异常提醒
        if abnormal_projects:
            admins = db.query(User).filter(
                or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
            ).all()
            
            alert_text = "⚠️ 发现项目数据异常：\n\n"
            for project, issue in abnormal_projects[:5]:  # 只显示前5个
                alert_text += f"• {project.project_name}: {issue}\n"
            
            if len(abnormal_projects) > 5:
                alert_text += f"• ...还有{len(abnormal_projects)-5}个异常项目\n"
            
            alert_text += "\n请及时处理异常项目数据。"
            
            for admin in admins:
                if admin.wechat_userid:
                    await notification_service._send_wechat_message(
                        admin.wechat_userid, 
                        alert_text
                    )
    
    async def _send_custom_reminder(self, user_id: int, message: str, related_project_id: Optional[int] = None):
        """发送自定义提醒"""
        with get_db_context() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.wechat_userid:
                notification_service = NotificationService(db)
                await notification_service._send_wechat_message(user.wechat_userid, message)
                
                print(f"⏰ 发送自定义提醒给 {user.username}: {message}")


# 全局提醒引擎实例
_reminder_engine = None

def get_reminder_engine() -> ReminderEngine:
    """获取提醒引擎实例 (单例模式)"""
    global _reminder_engine
    if _reminder_engine is None:
        _reminder_engine = ReminderEngine()
    return _reminder_engine