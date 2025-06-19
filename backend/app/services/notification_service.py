#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 通知服务
统一管理系统内所有通知，包括企业微信、邮件、站内信等
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import User, Project, Task, AIConversation
from app.wechat.utils import WeChatUtils
from app.ai.service import get_ai_service
from app import StatusEnum, RoleEnum

class NotificationService:
    """通知服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.wechat_utils = WeChatUtils()
        self.ai_service = get_ai_service()
        
        # 通知模板
        self.templates = {
            "project_created": "🎉 新项目创建通知\n\n项目：{project_name}\n客户：{customer_name}\n创建人：{creator_name}\n\n请关注项目进展！",
            "project_assigned": "📋 项目分配通知\n\n您被分配到新项目：\n{project_name}\n客户：{customer_name}\n截止时间：{deadline}\n\n请及时跟进！",
            "status_changed": "🔄 项目状态更新\n\n项目：{project_name}\n状态：{old_status} → {new_status}\n操作人：{operator_name}\n\n{ai_description}",
            "deadline_warning": "⏰ 项目截止提醒\n\n项目：{project_name}\n截止时间：{deadline}\n剩余：{remaining_days}天\n\n请注意时间安排！",
            "payment_reminder": "💰 收款提醒\n\n项目：{project_name}\n客户：{customer_name}\n金额：{amount}元\n类型：{payment_type}\n\n请跟进收款状态！",
            "task_assigned": "📌 任务分配通知\n\n任务：{task_title}\n项目：{project_name}\n截止：{due_date}\n\n请按时完成！",
            "overdue_alert": "🚨 逾期提醒\n\n项目：{project_name}\n已逾期：{overdue_days}天\n当前状态：{current_status}\n\n请尽快处理！"
        }
    
    async def send_project_assignment_notification(self, project: Project, assigner: User):
        """发送项目分配通知"""
        if not project.designer_id:
            return
        
        designer = self.db.query(User).filter(User.id == project.designer_id).first()
        if not designer or not designer.wechat_userid:
            return
        
        message = self.templates["project_assigned"].format(
            project_name=project.project_name,
            customer_name=project.customer_name,
            deadline=project.deadline.strftime('%Y-%m-%d') if project.deadline else "未设定"
        )
        
        await self._send_wechat_message(designer.wechat_userid, message)
        
        # 记录通知历史
        await self._log_notification(
            recipient_id=designer.id,
            notification_type="project_assignment",
            title="项目分配通知",
            content=message,
            related_project_id=project.id
        )
    
    async def send_status_change_notification(
        self, 
        project: Project, 
        old_status: str, 
        new_status: str, 
        operator: User
    ):
        """发送状态变更通知"""
        
        # 生成AI描述
        try:
            ai_description = await self.ai_service.generate_status_update(
                {
                    "project_name": project.project_name,
                    "customer_name": project.customer_name,
                    "project_number": project.project_number
                },
                old_status,
                new_status
            )
        except Exception:
            ai_description = "状态已更新，请关注项目进展。"
        
        message = self.templates["status_changed"].format(
            project_name=project.project_name,
            old_status=old_status,
            new_status=new_status,
            operator_name=operator.full_name or operator.username,
            ai_description=ai_description
        )
        
        # 确定通知对象
        recipients = await self._get_project_stakeholders(project, exclude_user_id=operator.id)
        
        # 发送通知
        for recipient in recipients:
            if recipient.wechat_userid:
                await self._send_wechat_message(recipient.wechat_userid, message)
        
        # 记录通知
        for recipient in recipients:
            await self._log_notification(
                recipient_id=recipient.id,
                notification_type="status_change",
                title="项目状态变更",
                content=message,
                related_project_id=project.id
            )
    
    async def send_deadline_warnings(self, days_ahead: int = 3):
        """发送截止日期警告"""
        warning_date = datetime.now().date() + timedelta(days=days_ahead)
        
        upcoming_projects = self.db.query(Project).filter(
            and_(
                Project.deadline == warning_date,
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        ).all()
        
        for project in upcoming_projects:
            # 通知项目相关人员
            stakeholders = await self._get_project_stakeholders(project)
            
            message = self.templates["deadline_warning"].format(
                project_name=project.project_name,
                deadline=project.deadline.strftime('%Y-%m-%d'),
                remaining_days=days_ahead
            )
            
            for stakeholder in stakeholders:
                if stakeholder.wechat_userid:
                    await self._send_wechat_message(stakeholder.wechat_userid, message)
                
                await self._log_notification(
                    recipient_id=stakeholder.id,
                    notification_type="deadline_warning",
                    title="截止日期提醒",
                    content=message,
                    related_project_id=project.id
                )
    
    async def send_payment_reminders(self):
        """发送收款提醒"""
        # 查找需要收定金的项目
        deposit_projects = self.db.query(Project).filter(
            and_(
                Project.status == StatusEnum.CONFIRMED,
                Project.deposit_paid == False
            )
        ).all()
        
        # 查找需要收尾款的项目
        final_payment_projects = self.db.query(Project).filter(
            and_(
                Project.status == StatusEnum.COMPLETED,
                Project.final_paid == False
            )
        ).all()
        
        # 发送定金提醒
        for project in deposit_projects:
            await self._send_payment_reminder(project, "定金")
        
        # 发送尾款提醒
        for project in final_payment_projects:
            await self._send_payment_reminder(project, "尾款")
    
    async def send_overdue_alerts(self):
        """发送逾期警告"""
        today = datetime.now().date()
        
        overdue_projects = self.db.query(Project).filter(
            and_(
                Project.deadline < today,
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        ).all()
        
        for project in overdue_projects:
            overdue_days = (today - project.deadline).days
            
            message = self.templates["overdue_alert"].format(
                project_name=project.project_name,
                overdue_days=overdue_days,
                current_status=project.status
            )
            
            # 通知项目负责人和管理员
            stakeholders = await self._get_project_stakeholders(project)
            admins = self.db.query(User).filter(
                or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
            ).all()
            
            all_recipients = list(set(stakeholders + admins))
            
            for recipient in all_recipients:
                if recipient.wechat_userid:
                    await self._send_wechat_message(recipient.wechat_userid, message)
                
                await self._log_notification(
                    recipient_id=recipient.id,
                    notification_type="overdue_alert",
                    title="项目逾期警告",
                    content=message,
                    related_project_id=project.id,
                    priority="high"
                )
    
    async def send_task_assignment_notification(self, task: Task):
        """发送任务分配通知"""
        if not task.assignee_id:
            return
        
        assignee = self.db.query(User).filter(User.id == task.assignee_id).first()
        if not assignee or not assignee.wechat_userid:
            return
        
        project = self.db.query(Project).filter(Project.id == task.project_id).first()
        
        message = self.templates["task_assigned"].format(
            task_title=task.title,
            project_name=project.project_name if project else "未知项目",
            due_date=task.due_date.strftime('%Y-%m-%d') if task.due_date else "未设定"
        )
        
        await self._send_wechat_message(assignee.wechat_userid, message)
        
        await self._log_notification(
            recipient_id=assignee.id,
            notification_type="task_assignment",
            title="任务分配通知",
            content=message,
            related_task_id=task.id
        )
    
    async def send_daily_summary(self, user: User):
        """发送每日工作摘要"""
        if not user.wechat_userid:
            return
        
        # 获取用户相关的项目和任务
        today = datetime.now().date()
        
        # 今日到期任务
        due_tasks = self.db.query(Task).filter(
            and_(
                Task.assignee_id == user.id,
                Task.due_date == today,
                Task.status != "completed"
            )
        ).all()
        
        # 需要关注的项目
        active_projects = self.db.query(Project).filter(
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
        
        summary = f"📊 {user.full_name or user.username} 的每日工作摘要\n\n"
        
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
        
        await self._send_wechat_message(user.wechat_userid, summary)
    
    async def send_weekly_report(self):
        """发送周报给管理员"""
        admins = self.db.query(User).filter(
            or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
        ).all()
        
        # 生成周报数据
        week_ago = datetime.now() - timedelta(days=7)
        
        # 本周新增项目
        new_projects = self.db.query(Project).filter(
            Project.created_at >= week_ago
        ).count()
        
        # 本周完成项目
        completed_projects = self.db.query(Project).filter(
            and_(
                Project.completed_at >= week_ago,
                Project.status == StatusEnum.COMPLETED
            )
        ).count()
        
        # 逾期项目
        overdue_projects = self.db.query(Project).filter(
            and_(
                Project.deadline < datetime.now().date(),
                Project.status.notin_([StatusEnum.COMPLETED, StatusEnum.ARCHIVED])
            )
        ).count()
        
        report = f"""📊 公司周报 ({datetime.now().strftime('%Y-%m-%d')})

📈 **本周数据**
- 新增项目：{new_projects}个
- 完成项目：{completed_projects}个
- 逾期项目：{overdue_projects}个

🎯 **运营状况**
"""
        
        if overdue_projects > 0:
            report += f"⚠️ 需要关注{overdue_projects}个逾期项目\n"
        else:
            report += "✅ 无逾期项目，运营状况良好\n"
        
        report += "\n📱 详细数据请查看Web管理界面"
        
        for admin in admins:
            if admin.wechat_userid:
                await self._send_wechat_message(admin.wechat_userid, report)
    
    # 私有方法
    async def _send_wechat_message(self, wechat_userid: str, message: str):
        """发送企业微信消息"""
        try:
            # 这里应该调用企业微信API发送消息
            # 暂时使用打印模拟
            print(f"📤 发送微信消息给 {wechat_userid}: {message}")
            
            # 实际实现应该类似：
            # success = self.wechat_utils.send_notification([wechat_userid], "通知", message)
            # return success
            
            return True
        except Exception as e:
            print(f"❌ 发送微信消息失败: {e}")
            return False
    
    async def _get_project_stakeholders(self, project: Project, exclude_user_id: int = None) -> List[User]:
        """获取项目相关人员"""
        stakeholder_ids = set()
        
        if project.creator_id and project.creator_id != exclude_user_id:
            stakeholder_ids.add(project.creator_id)
        
        if project.designer_id and project.designer_id != exclude_user_id:
            stakeholder_ids.add(project.designer_id)
        
        if project.sales_id and project.sales_id != exclude_user_id:
            stakeholder_ids.add(project.sales_id)
        
        if stakeholder_ids:
            return self.db.query(User).filter(User.id.in_(stakeholder_ids)).all()
        else:
            return []
    
    async def _send_payment_reminder(self, project: Project, payment_type: str):
        """发送收款提醒"""
        # 通知财务和管理员
        finance_users = self.db.query(User).filter(User.role == RoleEnum.FINANCE).all()
        admins = self.db.query(User).filter(
            or_(User.is_admin == True, User.role == RoleEnum.ADMIN)
        ).all()
        
        recipients = finance_users + admins
        
        amount = project.deposit_amount if payment_type == "定金" else project.final_price
        
        message = self.templates["payment_reminder"].format(
            project_name=project.project_name,
            customer_name=project.customer_name,
            amount=amount or "未设定",
            payment_type=payment_type
        )
        
        for recipient in recipients:
            if recipient.wechat_userid:
                await self._send_wechat_message(recipient.wechat_userid, message)
            
            await self._log_notification(
                recipient_id=recipient.id,
                notification_type="payment_reminder",
                title=f"{payment_type}提醒",
                content=message,
                related_project_id=project.id
            )
    
    async def _log_notification(
        self,
        recipient_id: int,
        notification_type: str,
        title: str,
        content: str,
        related_project_id: int = None,
        related_task_id: int = None,
        priority: str = "normal"
    ):
        """记录通知历史"""
        # 这里可以创建一个通知记录表来存储通知历史
        # 暂时使用AI对话记录表来模拟
        try:
            recipient = self.db.query(User).filter(User.id == recipient_id).first()
            
            conversation = AIConversation(
                user_id=recipient_id,
                project_id=related_project_id,
                wechat_userid=recipient.wechat_userid or f"user_{recipient_id}",
                message_type="notification",
                user_message=f"[系统通知] {title}",
                ai_response=content,
                intent=notification_type,
                confidence=1.0,
                created_at=datetime.utcnow()
            )
            
            self.db.add(conversation)
            self.db.commit()
            
        except Exception as e:
            print(f"❌ 记录通知历史失败: {e}")