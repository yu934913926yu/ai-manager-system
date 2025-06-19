#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 定时任务调度器
基于APScheduler实现的任务调度系统，支持多种触发器
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Callable, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from sqlalchemy.orm import Session
from app.database import get_db_context
from app.config import get_settings
from app.tasks.reminders import get_reminder_engine
from app.services.workflow_service import get_workflow_engine

settings = get_settings()
logger = logging.getLogger(__name__)

class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        # 配置调度器
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 30
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )
        
        self.is_running = False
        self.registered_jobs = {}
        
        print("✅ 定时任务调度器初始化完成")
    
    async def start(self):
        """启动调度器"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            
            # 注册默认任务
            await self._register_default_jobs()
            
            print("🚀 定时任务调度器已启动")
            logger.info("Task scheduler started successfully")
    
    async def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            print("🔴 定时任务调度器已停止")
            logger.info("Task scheduler stopped")
    
    def add_cron_job(
        self, 
        func: Callable, 
        job_id: str,
        cron_expression: str = None,
        hour: int = None,
        minute: int = None,
        day_of_week: str = None,
        **kwargs
    ):
        """添加Cron定时任务"""
        try:
            if cron_expression:
                # 使用cron表达式
                trigger = CronTrigger.from_crontab(cron_expression)
            else:
                # 使用参数构建
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    day_of_week=day_of_week
                )
            
            job = self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **kwargs
            )
            
            self.registered_jobs[job_id] = {
                "job": job,
                "type": "cron",
                "function": func.__name__,
                "created_at": datetime.now()
            }
            
            print(f"✅ Cron任务已添加: {job_id}")
            return job
            
        except Exception as e:
            print(f"❌ 添加Cron任务失败 {job_id}: {e}")
            logger.error(f"Failed to add cron job {job_id}: {e}")
            return None
    
    def add_interval_job(
        self, 
        func: Callable, 
        job_id: str,
        seconds: int = None,
        minutes: int = None,
        hours: int = None,
        **kwargs
    ):
        """添加间隔定时任务"""
        try:
            trigger = IntervalTrigger(
                seconds=seconds,
                minutes=minutes,
                hours=hours
            )
            
            job = self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **kwargs
            )
            
            self.registered_jobs[job_id] = {
                "job": job,
                "type": "interval",
                "function": func.__name__,
                "created_at": datetime.now()
            }
            
            print(f"✅ 间隔任务已添加: {job_id}")
            return job
            
        except Exception as e:
            print(f"❌ 添加间隔任务失败 {job_id}: {e}")
            logger.error(f"Failed to add interval job {job_id}: {e}")
            return None
    
    def add_one_time_job(
        self,
        func: Callable,
        job_id: str,
        run_date: datetime,
        **kwargs
    ):
        """添加一次性定时任务"""
        try:
            trigger = DateTrigger(run_date=run_date)
            
            job = self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **kwargs
            )
            
            self.registered_jobs[job_id] = {
                "job": job,
                "type": "one_time",
                "function": func.__name__,
                "run_date": run_date,
                "created_at": datetime.now()
            }
            
            print(f"✅ 一次性任务已添加: {job_id} (运行时间: {run_date})")
            return job
            
        except Exception as e:
            print(f"❌ 添加一次性任务失败 {job_id}: {e}")
            logger.error(f"Failed to add one-time job {job_id}: {e}")
            return None
    
    def remove_job(self, job_id: str):
        """移除任务"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.registered_jobs:
                del self.registered_jobs[job_id]
            print(f"✅ 任务已移除: {job_id}")
            
        except Exception as e:
            print(f"❌ 移除任务失败 {job_id}: {e}")
            logger.error(f"Failed to remove job {job_id}: {e}")
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        jobs_info = []
        
        for job_id, job_info in self.registered_jobs.items():
            job = job_info["job"]
            jobs_info.append({
                "job_id": job_id,
                "function": job_info["function"],
                "type": job_info["type"],
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "created_at": job_info["created_at"].isoformat(),
                "is_active": True
            })
        
        return jobs_info
    
    def pause_job(self, job_id: str):
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            print(f"⏸️ 任务已暂停: {job_id}")
        except Exception as e:
            print(f"❌ 暂停任务失败 {job_id}: {e}")
    
    def resume_job(self, job_id: str):
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            print(f"▶️ 任务已恢复: {job_id}")
        except Exception as e:
            print(f"❌ 恢复任务失败 {job_id}: {e}")
    
    async def _register_default_jobs(self):
        """注册默认任务"""
        print("📋 注册默认定时任务...")
        
        try:
            # 1. 每日早上9点发送提醒
            self.add_cron_job(
                func=self._daily_morning_reminders,
                job_id="daily_morning_reminders",
                hour=9,
                minute=0
            )
            
            # 2. 每小时检查紧急任务
            self.add_interval_job(
                func=self._hourly_urgent_check,
                job_id="hourly_urgent_check",
                hours=1
            )
            
            # 3. 每日晚上8点处理工作流
            self.add_cron_job(
                func=self._daily_workflow_processing,
                job_id="daily_workflow_processing",
                hour=20,
                minute=0
            )
            
            # 4. 每周一早上生成周报
            self.add_cron_job(
                func=self._weekly_report_generation,
                job_id="weekly_report_generation",
                day_of_week='mon',
                hour=8,
                minute=30
            )
            
            # 5. 每30分钟系统健康检查
            self.add_interval_job(
                func=self._system_health_check,
                job_id="system_health_check",
                minutes=30
            )
            
            # 6. 每日凌晨2点数据清理
            self.add_cron_job(
                func=self._daily_data_cleanup,
                job_id="daily_data_cleanup",
                hour=2,
                minute=0
            )
            
            print("✅ 默认定时任务注册完成")
            
        except Exception as e:
            print(f"❌ 注册默认任务失败: {e}")
            logger.error(f"Failed to register default jobs: {e}")
    
    async def _daily_morning_reminders(self):
        """每日早上提醒任务"""
        print("🌅 执行每日早上提醒任务...")
        
        try:
            reminder_engine = get_reminder_engine()
            await reminder_engine.send_daily_reminders()
            
            print("✅ 每日早上提醒任务完成")
            
        except Exception as e:
            print(f"❌ 每日早上提醒任务失败: {e}")
            logger.error(f"Daily morning reminders failed: {e}")
    
    async def _hourly_urgent_check(self):
        """每小时紧急检查"""
        print("⏰ 执行每小时紧急检查...")
        
        try:
            reminder_engine = get_reminder_engine()
            await reminder_engine.check_urgent_items()
            
            print("✅ 每小时紧急检查完成")
            
        except Exception as e:
            print(f"❌ 每小时紧急检查失败: {e}")
            logger.error(f"Hourly urgent check failed: {e}")
    
    async def _daily_workflow_processing(self):
        """每日工作流处理"""
        print("🔄 执行每日工作流处理...")
        
        try:
            with get_db_context() as db:
                workflow_engine = get_workflow_engine(db)
                await workflow_engine.process_scheduled_workflows()
            
            print("✅ 每日工作流处理完成")
            
        except Exception as e:
            print(f"❌ 每日工作流处理失败: {e}")
            logger.error(f"Daily workflow processing failed: {e}")
    
    async def _weekly_report_generation(self):
        """周报生成"""
        print("📊 执行周报生成...")
        
        try:
            with get_db_context() as db:
                # 这里可以添加周报生成逻辑
                print("📝 周报生成功能待实现")
            
            print("✅ 周报生成完成")
            
        except Exception as e:
            print(f"❌ 周报生成失败: {e}")
            logger.error(f"Weekly report generation failed: {e}")
    
    async def _system_health_check(self):
        """系统健康检查"""
        print("🔍 执行系统健康检查...")
        
        try:
            from app.monitoring.health import get_health_monitor
            
            health_monitor = get_health_monitor()
            health_status = await health_monitor.comprehensive_health_check()
            
            # 如果有严重问题，发送告警
            if health_status.get("status") == "unhealthy":
                print("🚨 检测到系统健康问题！")
                # 这里可以添加告警逻辑
            
            print("✅ 系统健康检查完成")
            
        except Exception as e:
            print(f"❌ 系统健康检查失败: {e}")
            logger.error(f"System health check failed: {e}")
    
    async def _daily_data_cleanup(self):
        """每日数据清理"""
        print("🧹 执行每日数据清理...")
        
        try:
            # 清理过期日志、临时文件等
            cleanup_date = datetime.now() - timedelta(days=30)
            
            with get_db_context() as db:
                # 清理30天前的AI对话记录（可选）
                from app.models import AIConversation
                old_conversations = db.query(AIConversation).filter(
                    AIConversation.created_at < cleanup_date
                ).count()
                
                if old_conversations > 1000:  # 如果记录太多，清理一些
                    db.query(AIConversation).filter(
                        AIConversation.created_at < cleanup_date
                    ).limit(500).delete()
                    db.commit()
                    print(f"🗑️ 清理了 500 条旧对话记录")
            
            print("✅ 每日数据清理完成")
            
        except Exception as e:
            print(f"❌ 每日数据清理失败: {e}")
            logger.error(f"Daily data cleanup failed: {e}")


# 全局调度器实例
_scheduler = None

def get_scheduler() -> TaskScheduler:
    """获取调度器实例 (单例模式)"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler

async def init_scheduler():
    """初始化并启动调度器"""
    scheduler = get_scheduler()
    await scheduler.start()
    return scheduler

async def shutdown_scheduler():
    """关闭调度器"""
    scheduler = get_scheduler()
    await scheduler.stop()