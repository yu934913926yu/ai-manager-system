"""
AI服务核心调用模块
支持Claude、Gemini等多种AI服务
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx
from app.config import get_settings
from app.ai.prompts import PromptManager
from app.ai.monitor import AIMonitor

settings = get_settings()

class AIService:
    """AI服务管理器"""
    
    def __init__(self):
        self.claude_api_key = settings.CLAUDE_API_KEY
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.timeout = settings.AI_TIMEOUT
        self.max_tokens = settings.AI_MAX_TOKENS
        self.temperature = settings.AI_TEMPERATURE
        
        self.prompt_manager = PromptManager()
        self.monitor = AIMonitor()
        
        # API endpoints
        self.claude_endpoint = "https://api.anthropic.com/v1/messages"
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    async def chat_completion(
        self, 
        message: str, 
        context: Dict[str, Any] = None,
        model: str = "claude"
    ) -> Dict[str, Any]:
        """智能对话完成"""
        start_time = time.time()
        
        try:
            if model.lower() == "claude":
                response = await self._call_claude(message, context)
            elif model.lower() == "gemini":
                response = await self._call_gemini(message, context)
            else:
                raise ValueError(f"不支持的AI模型: {model}")
            
            # 记录监控数据
            self.monitor.record_call(
                model=model,
                input_tokens=len(message.split()),
                output_tokens=len(response.get("content", "").split()),
                cost=response.get("cost", 0),
                latency=time.time() - start_time,
                success=True
            )
            
            return response
            
        except Exception as e:
            self.monitor.record_call(
                model=model,
                input_tokens=len(message.split()),
                output_tokens=0,
                cost=0,
                latency=time.time() - start_time,
                success=False,
                error=str(e)
            )
            raise
    
    async def _call_claude(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用Claude API"""
        if not self.claude_api_key:
            raise ValueError("Claude API密钥未配置")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.claude_api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # 构建请求数据
        messages = []
        if context:
            system_prompt = self.prompt_manager.get_system_prompt(context)
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.claude_endpoint, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            return {
                "content": result["content"][0]["text"],
                "model": "claude",
                "usage": result.get("usage", {}),
                "cost": self._calculate_claude_cost(result.get("usage", {}))
            }
    
    async def _call_gemini(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用Gemini API"""
        if not self.gemini_api_key:
            raise ValueError("Gemini API密钥未配置")
        
        url = f"{self.gemini_endpoint}?key={self.gemini_api_key}"
        
        # 构建提示词
        prompt = message
        if context:
            system_prompt = self.prompt_manager.get_system_prompt(context)
            prompt = f"{system_prompt}\n\n用户问题：{message}"
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
            return {
                "content": content,
                "model": "gemini",
                "usage": result.get("usageMetadata", {}),
                "cost": self._calculate_gemini_cost(result.get("usageMetadata", {}))
            }
    
    def _calculate_claude_cost(self, usage: Dict) -> float:
        """计算Claude调用成本"""
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        # Claude 3 Sonnet定价 (假设)
        input_cost = input_tokens * 0.000003  # $3/1M tokens
        output_cost = output_tokens * 0.000015  # $15/1M tokens
        
        return input_cost + output_cost
    
    def _calculate_gemini_cost(self, usage: Dict) -> float:
        """计算Gemini调用成本"""
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        
        # Gemini Pro定价 (假设)
        input_cost = input_tokens * 0.00000035  # $0.35/1M tokens
        output_cost = output_tokens * 0.00000105  # $1.05/1M tokens
        
        return input_cost + output_cost

    async def analyze_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """项目智能分析"""
        prompt = self.prompt_manager.get_project_analysis_prompt(project_data)
        response = await self.chat_completion(prompt, {"type": "project_analysis"})
        
        try:
            # 尝试解析结构化响应
            analysis = json.loads(response["content"])
        except json.JSONDecodeError:
            # 如果不是JSON，则包装为简单结构
            analysis = {
                "summary": response["content"],
                "suggestions": [],
                "risks": [],
                "priority": "normal"
            }
        
        return analysis
    
    async def generate_status_update(self, project_data: Dict, old_status: str, new_status: str) -> str:
        """生成状态更新说明"""
        prompt = self.prompt_manager.get_status_update_prompt(project_data, old_status, new_status)
        response = await self.chat_completion(prompt, {"type": "status_update"})
        return response["content"]
    
    async def extract_project_info(self, text: str) -> Dict[str, Any]:
        """从文本中提取项目信息"""
        prompt = self.prompt_manager.get_extraction_prompt(text)
        response = await self.chat_completion(prompt, {"type": "information_extraction"})
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return {"error": "无法解析项目信息", "raw_text": text}
    
    async def generate_reminder_text(self, reminder_type: str, data: Dict[str, Any]) -> str:
        """生成提醒文本"""
        prompt = self.prompt_manager.get_reminder_prompt(reminder_type, data)
        response = await self.chat_completion(prompt, {"type": "reminder_generation"})
        return response["content"]

# 全局AI服务实例
_ai_service = None

def get_ai_service() -> AIService:
    """获取AI服务实例 (单例模式)"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
