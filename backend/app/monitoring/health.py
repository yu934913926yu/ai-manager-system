#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 系统健康监控
监控数据库、AI服务、企业微信等关键组件的运行状态
"""

import asyncio
import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db_context, test_connection, get_db_status
from app.config import get_settings
from app.ai.service import get_ai_service
from app.ai.monitor import get_ai_monitor
from app.wechat.bot import get_wechat_bot

settings = get_settings()

class HealthMonitor:
    """系统健康监控器"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.ai_monitor = get_ai_monitor()
        
        # 健康检查配置
        self.health_thresholds = {
            "cpu_usage_max": 80.0,          # CPU使用率上限
            "memory_usage_max": 85.0,       # 内存使用率上限
            "disk_usage_max": 90.0,         # 磁盘使用率上限
            "db_response_time_max": 5.0,    # 数据库响应时间上限(秒)
            "ai_error_rate_max": 10.0,      # AI错误率上限(%)
            "api_response_time_max": 2.0    # API响应时间上限(秒)
        }
        
        self.health_history = []
        print("✅ 健康监控器初始化完成")
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """全面健康检查"""
        start_time = time.time()
        
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "components": {},
            "warnings": [],
            "errors": [],
            "performance": {}
        }
        
        # 1. 系统资源检查
        system_health = await self._check_system_resources()
        health_status["components"]["system"] = system_health
        
        # 2. 数据库健康检查
        database_health = await self._check_database_health()
        health_status["components"]["database"] = database_health
        
        # 3. AI服务健康检查
        ai_health = await self._check_ai_services()
        health_status["components"]["ai"] = ai_health
        
        # 4. 企业微信健康检查
        wechat_health = await self._check_wechat_health()
        health_status["components"]["wechat"] = wechat_health
        
        # 5. 应用性能检查
        performance_metrics = await self._check_performance_metrics()
        health_status["performance"] = performance_metrics
        
        # 汇总状态
        component_statuses = [
            comp["status"] for comp in health_status["components"].values()
        ]
        
        if "critical" in component_statuses:
            health_status["status"] = "critical"
        elif "unhealthy" in component_statuses:
            health_status["status"] = "unhealthy"
        elif "warning" in component_statuses:
            health_status["status"] = "warning"
        
        # 记录检查时间
        health_status["check_duration"] = round(time.time() - start_time, 3)
        
        # 保存健康历史
        self._save_health_history(health_status)
        
        return health_status
    
    async def quick_health_check(self) -> Dict[str, Any]:
        """快速健康检查"""
        start_time = time.time()
        
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "database": await self._quick_database_check(),
            "ai_service": await self._quick_ai_check(),
            "system_load": self._get_system_load(),
            "check_duration": 0
        }
        
        # 简单状态评估
        if not health_status["database"]["connected"]:
            health_status["status"] = "critical"
        elif health_status["system_load"]["cpu_percent"] > 90:
            health_status["status"] = "warning"
        
        health_status["check_duration"] = round(time.time() - start_time, 3)
        
        return health_status
    
    async def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取健康历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            record for record in self.health_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_time
        ]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康汇总"""
        if not self.health_history:
            return {"message": "No health data available"}
        
        recent_checks = self.health_history[-10:]  # 最近10次检查
        
        # 计算平均性能指标
        avg_cpu = sum(check.get("performance", {}).get("cpu_usage", 0) for check in recent_checks) / len(recent_checks)
        avg_memory = sum(check.get("performance", {}).get("memory_usage", 0) for check in recent_checks) / len(recent_checks)
        
        # 统计状态分布
        status_counts = {}
        for check in recent_checks:
            status = check.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "recent_checks": len(recent_checks),
            "avg_cpu_usage": round(avg_cpu, 2),
            "avg_memory_usage": round(avg_memory, 2),
            "status_distribution": status_counts,
            "last_check": recent_checks[-1]["timestamp"] if recent_checks else None
        }
    
    # 私有方法
    async def _check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 进程信息
            process_count = len(psutil.pids())
            
            # 负载平均值 (Linux/Mac)
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                load_avg = [0, 0, 0]  # Windows不支持
            
            status = "healthy"
            warnings = []
            
            # 检查阈值
            if cpu_percent > self.health_thresholds["cpu_usage_max"]:
                status = "warning"
                warnings.append(f"CPU使用率过高: {cpu_percent}%")
            
            if memory_percent > self.health_thresholds["memory_usage_max"]:
                status = "warning"  
                warnings.append(f"内存使用率过高: {memory_percent}%")
            
            if disk_percent > self.health_thresholds["disk_usage_max"]:
                status = "critical"
                warnings.append(f"磁盘使用率过高: {disk_percent}%")
            
            return {
                "status": status,
                "warnings": warnings,
                "metrics": {
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory_percent, 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": round(disk_percent, 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                    "process_count": process_count,
                    "load_average": [round(x, 2) for x in load_avg]
                }
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "warnings": ["无法获取系统资源信息"]
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康"""
        try:
            start_time = time.time()
            
            # 测试连接
            db_connected = test_connection()
            connection_time = time.time() - start_time
            
            if not db_connected:
                return {
                    "status": "critical",
                    "connected": False,
                    "error": "数据库连接失败"
                }
            
            # 获取数据库状态
            db_status = get_db_status()
            
            # 测试查询性能
            with get_db_context() as db:
                query_start = time.time()
                result = db.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                query_time = time.time() - query_start
                
                # 检查表状态
                table_checks = await self._check_database_tables(db)
            
            status = "healthy"
            warnings = []
            
            # 检查响应时间
            if connection_time > self.health_thresholds["db_response_time_max"]:
                status = "warning"
                warnings.append(f"数据库响应时间过长: {connection_time:.2f}s")
            
            return {
                "status": status,
                "connected": True,
                "warnings": warnings,
                "metrics": {
                    "connection_time": round(connection_time, 3),
                    "query_time": round(query_time, 3),
                    "user_count": user_count,
                    "database_info": db_status,
                    "table_status": table_checks
                }
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "connected": False,
                "error": str(e)
            }
    
    async def _check_database_tables(self, db: Session) -> Dict[str, Any]:
        """检查数据库表状态"""
        table_checks = {}
        
        try:
            # 检查主要表的记录数
            tables_to_check = [
                ("users", "用户表"),
                ("projects", "项目表"),
                ("tasks", "任务表"),
                ("suppliers", "供应商表")
            ]
            
            for table_name, description in tables_to_check:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    table_checks[table_name] = {
                        "description": description,
                        "record_count": count,
                        "status": "ok"
                    }
                except Exception as e:
                    table_checks[table_name] = {
                        "description": description,
                        "status": "error",
                        "error": str(e)
                    }
            
        except Exception as e:
            table_checks["error"] = str(e)
        
        return table_checks
    
    async def _check_ai_services(self) -> Dict[str, Any]:
        """检查AI服务健康"""
        try:
            # 获取AI监控数据
            ai_stats = self.ai_monitor.get_hourly_stats(hours=1)
            daily_stats = self.ai_monitor.get_daily_stats()
            
            status = "healthy"
            warnings = []
            
            # 检查错误率
            if ai_stats["success_rate"] < (100 - self.health_thresholds["ai_error_rate_max"]):
                status = "warning"
                warnings.append(f"AI服务错误率过高: {100 - ai_stats['success_rate']:.1f}%")
            
            # 检查每日限制
            if daily_stats["cost"] > self.ai_monitor.daily_limits["max_cost"]:
                status = "warning"
                warnings.append(f"AI服务成本超限: ${daily_stats['cost']:.2f}")
            
            # 简单测试AI服务
            test_start = time.time()
            try:
                test_response = await self.ai_service.chat_completion(
                    "系统健康检查测试", 
                    {"type": "health_check"}
                )
                ai_response_time = time.time() - test_start
                ai_available = True
            except Exception as e:
                ai_response_time = time.time() - test_start
                ai_available = False
                warnings.append(f"AI服务测试失败: {str(e)}")
                status = "unhealthy"
            
            return {
                "status": status,
                "available": ai_available,
                "warnings": warnings,
                "metrics": {
                    "hourly_stats": ai_stats,
                    "daily_stats": daily_stats,
                    "response_time": round(ai_response_time, 3),
                    "api_limits": self.ai_monitor.daily_limits
                }
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "available": False,
                "error": str(e)
            }
    
    async def _check_wechat_health(self) -> Dict[str, Any]:
        """检查企业微信健康"""
        try:
            wechat_bot = get_wechat_bot()
            
            if not wechat_bot:
                return {
                    "status": "warning",
                    "available": False,
                    "message": "企业微信机器人未初始化"
                }
            
            # 获取机器人状态
            bot_status = wechat_bot.get_bot_status()
            
            status = "healthy"
            if bot_status["status"] != "online":
                status = "unhealthy"
            
            return {
                "status": status,
                "available": bot_status["status"] == "online",
                "bot_status": bot_status
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "available": False,
                "error": str(e)
            }
    
    async def _check_performance_metrics(self) -> Dict[str, Any]:
        """检查性能指标"""
        try:
            # 系统负载
            system_load = self._get_system_load()
            
            # 应用启动时间 (简单估算)
            try:
                boot_time = psutil.boot_time()
                uptime_seconds = time.time() - boot_time
                uptime_hours = uptime_seconds / 3600
            except:
                uptime_hours = 0
            
            # 网络连接测试
            network_start = time.time()
            try:
                import requests
                response = requests.get("https://www.baidu.com", timeout=5)
                network_latency = time.time() - network_start
                network_available = response.status_code == 200
            except:
                network_latency = time.time() - network_start
                network_available = False
            
            return {
                "system_load": system_load,
                "uptime_hours": round(uptime_hours, 2),
                "network": {
                    "available": network_available,
                    "latency": round(network_latency, 3)
                }
            }
            
        except Exception as e:
            return {
                "error": str(e)
            }
    
    def _get_system_load(self) -> Dict[str, Any]:
        """获取系统负载"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2)
            }
        except:
            return {}
    
    async def _quick_database_check(self) -> Dict[str, Any]:
        """快速数据库检查"""
        try:
            start_time = time.time()
            connected = test_connection()
            response_time = time.time() - start_time
            
            return {
                "connected": connected,
                "response_time": round(response_time, 3)
            }
        except:
            return {
                "connected": False,
                "response_time": 0
            }
    
    async def _quick_ai_check(self) -> Dict[str, Any]:
        """快速AI服务检查"""
        try:
            daily_stats = self.ai_monitor.get_daily_stats()
            
            return {
                "daily_calls": daily_stats["calls"],
                "daily_cost": daily_stats["cost"],
                "within_limits": daily_stats["cost"] < self.ai_monitor.daily_limits["max_cost"]
            }
        except:
            return {
                "daily_calls": 0,
                "daily_cost": 0,
                "within_limits": True
            }
    
    def _save_health_history(self, health_status: Dict[str, Any]):
        """保存健康检查历史"""
        self.health_history.append(health_status)
        
        # 只保留最近100次记录
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]


# 全局健康监控实例
_health_monitor = None

def get_health_monitor() -> HealthMonitor:
    """获取健康监控实例 (单例模式)"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor