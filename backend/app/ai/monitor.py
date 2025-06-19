"""
AI调用监控和成本控制
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

@dataclass
class AICallRecord:
    """AI调用记录"""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency: float
    success: bool
    error: Optional[str] = None
    user_id: Optional[int] = None
    operation: Optional[str] = None

class AIMonitor:
    """AI调用监控器"""
    
    def __init__(self):
        self.call_records: List[AICallRecord] = []
        self.daily_limits = {
            "max_calls": 1000,
            "max_cost": 50.0,  # $50 per day
            "max_tokens": 100000
        }
        self.current_daily_stats = {
            "calls": 0,
            "cost": 0.0,
            "tokens": 0,
            "date": datetime.now().date()
        }
    
    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency: float,
        success: bool,
        error: Optional[str] = None,
        user_id: Optional[int] = None,
        operation: Optional[str] = None
    ):
        """记录AI调用"""
        record = AICallRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency=latency,
            success=success,
            error=error,
            user_id=user_id,
            operation=operation
        )
        
        self.call_records.append(record)
        self._update_daily_stats(record)
        
        # 检查是否超过限制
        self._check_limits()
    
    def _update_daily_stats(self, record: AICallRecord):
        """更新每日统计"""
        today = datetime.now().date()
        
        # 如果是新的一天，重置统计
        if self.current_daily_stats["date"] != today:
            self.current_daily_stats = {
                "calls": 0,
                "cost": 0.0,
                "tokens": 0,
                "date": today
            }
        
        # 更新统计
        self.current_daily_stats["calls"] += 1
        self.current_daily_stats["cost"] += record.cost
        self.current_daily_stats["tokens"] += record.input_tokens + record.output_tokens
    
    def _check_limits(self):
        """检查是否超过限制"""
        stats = self.current_daily_stats
        
        if stats["calls"] > self.daily_limits["max_calls"]:
            print(f"⚠️ 警告：每日调用次数超限 ({stats['calls']}/{self.daily_limits['max_calls']})")
        
        if stats["cost"] > self.daily_limits["max_cost"]:
            print(f"⚠️ 警告：每日成本超限 (${stats['cost']:.2f}/${self.daily_limits['max_cost']})")
        
        if stats["tokens"] > self.daily_limits["max_tokens"]:
            print(f"⚠️ 警告：每日token数超限 ({stats['tokens']}/{self.daily_limits['max_tokens']})")
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """获取每日统计"""
        return dict(self.current_daily_stats)
    
    def get_hourly_stats(self, hours: int = 24) -> Dict[str, Any]:
        """获取小时统计"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_records = [r for r in self.call_records if r.timestamp > cutoff_time]
        
        if not recent_records:
            return {"total_calls": 0, "total_cost": 0, "total_tokens": 0, "success_rate": 0}
        
        total_calls = len(recent_records)
        total_cost = sum(r.cost for r in recent_records)
        total_tokens = sum(r.input_tokens + r.output_tokens for r in recent_records)
        successful_calls = sum(1 for r in recent_records if r.success)
        success_rate = successful_calls / total_calls * 100
        
        return {
            "total_calls": total_calls,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "success_rate": round(success_rate, 2),
            "avg_latency": round(sum(r.latency for r in recent_records) / total_calls, 3),
            "model_distribution": self._get_model_distribution(recent_records)
        }
    
    def _get_model_distribution(self, records: List[AICallRecord]) -> Dict[str, int]:
        """获取模型使用分布"""
        distribution = defaultdict(int)
        for record in records:
            distribution[record.model] += 1
        return dict(distribution)
    
    def get_error_summary(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取错误摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_records = [
            r for r in self.call_records 
            if r.timestamp > cutoff_time and not r.success
        ]
        
        error_summary = defaultdict(int)
        for record in error_records:
            error_summary[record.error or "Unknown error"] += 1
        
        return [
            {"error": error, "count": count}
            for error, count in error_summary.items()
        ]
    
    def check_rate_limit(self, user_id: int, window_minutes: int = 60, max_calls: int = 100) -> bool:
        """检查用户速率限制"""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        user_calls = [
            r for r in self.call_records 
            if r.timestamp > cutoff_time and r.user_id == user_id
        ]
        
        return len(user_calls) < max_calls
    
    def export_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """导出统计数据"""
        filtered_records = [
            r for r in self.call_records 
            if start_date <= r.timestamp <= end_date
        ]
        
        if not filtered_records:
            return {"message": "No data in specified date range"}
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_calls": len(filtered_records),
                "successful_calls": sum(1 for r in filtered_records if r.success),
                "total_cost": round(sum(r.cost for r in filtered_records), 4),
                "total_tokens": sum(r.input_tokens + r.output_tokens for r in filtered_records),
                "avg_latency": round(sum(r.latency for r in filtered_records) / len(filtered_records), 3)
            },
            "model_stats": self._get_model_distribution(filtered_records),
            "daily_breakdown": self._get_daily_breakdown(filtered_records)
        }
    
    def _get_daily_breakdown(self, records: List[AICallRecord]) -> Dict[str, Dict[str, Any]]:
        """获取每日分解数据"""
        daily_data = defaultdict(lambda: {"calls": 0, "cost": 0, "tokens": 0})
        
        for record in records:
            date_key = record.timestamp.strftime("%Y-%m-%d")
            daily_data[date_key]["calls"] += 1
            daily_data[date_key]["cost"] += record.cost
            daily_data[date_key]["tokens"] += record.input_tokens + record.output_tokens
        
        return dict(daily_data)

# 全局监控实例
_ai_monitor = None

def get_ai_monitor() -> AIMonitor:
    """获取AI监控实例"""
    global _ai_monitor
    if _ai_monitor is None:
        _ai_monitor = AIMonitor()
    return _ai_monitor