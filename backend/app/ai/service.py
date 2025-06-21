#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - AI服务实现
集成Claude和Gemini API，提供统一的AI服务接口
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from abc import ABC, abstractmethod

from app.config import get_settings
from app.ai.monitor import get_ai_monitor

settings = get_settings()

class AIProvider(ABC):
    """AI提供商基类"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成AI响应"""
        pass
    
    @abstractmethod
    async def analyze_image(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """分析图片"""
        pass

class ClaudeProvider(AIProvider):
    """Claude AI提供商"""
    
    def __init__(self):
        self.api_key = settings.CLAUDE_API_KEY
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-3-haiku-20240307"
        self.monitor = get_ai_monitor()
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """调用Claude API生成响应"""
        if not self.api_key:
            return {"success": False, "error": "Claude API密钥未配置"}
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"]
                    
                    # 记录调用
                    self.monitor.record_call(
                        model=self.model,
                        input_tokens=result.get("usage", {}).get("input_tokens", 0),
                        output_tokens=result.get("usage", {}).get("output_tokens", 0),
                        latency=response.elapsed.total_seconds(),
                        success=True
                    )
                    
                    return {
                        "success": True,
                        "content": content,
                        "usage": result.get("usage", {})
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API错误: {response.status_code}"
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def analyze_image(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """使用Claude分析图片"""
        # Claude视觉API实现
        return {"success": False, "error": "Claude视觉功能待实现"}

class GeminiProvider(AIProvider):
    """Gemini AI提供商"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-pro"
        self.vision_model = "gemini-pro-vision"
        self.monitor = get_ai_monitor()
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """调用Gemini API生成响应"""
        if not self.api_key:
            return {"success": False, "error": "Gemini API密钥未配置"}
        
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 1000)
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=30.0)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # 记录调用
                    self.monitor.record_call(
                        model=self.model,
                        input_tokens=len(prompt.split()),  # 估算
                        output_tokens=len(content.split()),  # 估算
                        latency=response.elapsed.total_seconds(),
                        success=True
                    )
                    
                    return {
                        "success": True,
                        "content": content
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API错误: {response.status_code}"
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def analyze_image(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """使用Gemini分析图片"""
        if not self.api_key:
            return {"success": False, "error": "Gemini API密钥未配置"}
        
        # Gemini Vision API实现
        import base64
        
        url = f"{self.base_url}/models/{self.vision_model}:generateContent?key={self.api_key}"
        
        image_base64 = base64.b64encode(image_data).decode()
        
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=30.0)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    return {
                        "success": True,
                        "content": content
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API错误: {response.status_code}"
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)}

class AIService:
    """统一的AI服务接口"""
    
    def __init__(self):
        self.providers = {
            "claude": ClaudeProvider(),
            "gemini": GeminiProvider()
        }
        self.default_provider = "gemini" if settings.GEMINI_API_KEY else "claude"
        
        # 提示词模板
        self.prompts = {
            "project_analysis": """分析以下项目信息并提供专业建议：
项目名称：{project_name}
客户：{customer_name}
项目类型：{project_type}
预算：{budget}

请提供：
1. 项目风险评估
2. 时间规划建议
3. 资源配置建议
4. 潜在问题预警""",
            
            "ocr_extract": """从以下OCR识别的文本中提取项目信息：

{ocr_text}

请提取并返回JSON格式：
{{
    "customer_name": "客户名称",
    "project_name": "项目名称",
    "amount": "金额",
    "phone": "电话",
    "email": "邮箱",
    "deadline": "截止日期",
    "requirements": "需求描述"
}}""",
            
            "status_suggestion": """项目当前状态：{current_status}
项目创建时间：{created_at}
最后更新：{updated_at}

请建议下一步操作和注意事项。"""
        }
    
    async def analyze_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI项目分析"""
        prompt = self.prompts["project_analysis"].format(
            project_name=project_data.get("project_name", "未知"),
            customer_name=project_data.get("customer_name", "未知"),
            project_type=project_data.get("project_type", "设计"),
            budget=project_data.get("quoted_price", "待定")
        )
        
        provider = self.providers.get(self.default_provider)
        if not provider:
            return {"success": False, "error": "AI服务未配置"}
        
        result = await provider.generate_response(prompt)
        
        if result["success"]:
            try:
                # 解析AI响应
                content = result["content"]
                
                # 简单的解析逻辑
                suggestions = []
                lines = content.split("\n")
                for line in lines:
                    if line.strip() and not line.startswith("#"):
                        suggestions.append(line.strip())
                
                return {
                    "success": True,
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "suggestions": suggestions[:5],  # 最多5条建议
                    "full_analysis": content
                }
            except:
                return {
                    "success": True,
                    "summary": result["content"],
                    "suggestions": []
                }
        
        return result
    
    async def extract_from_ocr(self, ocr_text: str) -> Dict[str, Any]:
        """从OCR文本提取项目信息"""
        prompt = self.prompts["ocr_extract"].format(ocr_text=ocr_text)
        
        provider = self.providers.get(self.default_provider)
        if not provider:
            return {"success": False, "error": "AI服务未配置"}
        
        result = await provider.generate_response(prompt, temperature=0.3)
        
        if result["success"]:
            try:
                # 尝试解析JSON
                import re
                content = result["content"]
                
                # 查找JSON部分
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group()
                    extracted_info = json.loads(json_str)
                    
                    return {
                        "success": True,
                        "extracted_info": extracted_info
                    }
            except:
                pass
        
        return {"success": False, "error": "信息提取失败"}
    
    async def generate_status_suggestion(self, project_info: Dict[str, Any]) -> str:
        """生成状态更新建议"""
        prompt = self.prompts["status_suggestion"].format(
            current_status=project_info.get("status", "未知"),
            created_at=project_info.get("created_at", "未知"),
            updated_at=project_info.get("updated_at", "未知")
        )
        
        provider = self.providers.get(self.default_provider)
        if not provider:
            return "AI服务暂时不可用"
        
        result = await provider.generate_response(prompt, max_tokens=500)
        
        if result["success"]:
            return result["content"]
        
        return "暂无建议"

# 单例模式
_ai_service = None

def get_ai_service() -> AIService:
    """获取AI服务实例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service