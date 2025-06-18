#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 企业微信机器人核心
处理企业微信消息的核心逻辑
"""

import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

from wechatpy.enterprise import WeChatEnterprise
from wechatpy.enterprise.crypto import WeChatEnterpriseCrypto
from wechatpy.exceptions import WeChatException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db_context
from app.models import User, AIConversation
from app.wechat.handlers import MessageHandler
from app.wechat.utils import WeChatUtils

settings = get_settings()

class WeChatBot:
    """企业微信机器人"""
    
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.secret = settings.WECHAT_CORP_SECRET
        self.agent_id = settings.WECHAT_AGENT_ID
        
        if not all([self.corp_id, self.secret, self.agent_id]):
            raise ValueError("企业微信配置不完整")
        
        # 初始化企业微信客户端
        self.wechat = WeChatEnterprise(self.corp_id, self.secret)
        self.message_handler = MessageHandler()
        self.utils = WeChatUtils()
        
    def handle_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理接收到的消息"""
        start_time = time.time()
        
        try:
            # 提取消息基本信息
            msg_type = data.get('MsgType', 'text')
            from_user = data.get('FromUserName', '')
            content = data.get('Content', '')
            
            print(f"📨 收到消息: {from_user} -> {content[:50]}...")
            
            # 获取用户信息
            user = self._get_user_by_wechat_id(from_user)
            
            # 处理不同类型的消息
            if msg_type == 'text':
                response = self.message_handler.handle_text_message(
                    content, from_user, user
                )
            elif msg_type == 'image':
                response = self.message_handler.handle_image_message(
                    data, from_user, user
                )
            elif msg_type == 'file':
                response = self.message_handler.handle_file_message(
                    data, from_user, user
                )
            else:
                response = "抱歉，我暂时不支持这种消息类型。"
            
            # 记录对话历史
            processing_time = time.time() - start_time
            self._save_conversation(from_user, content, response, user, processing_time)
            
            # 发送回复
            self.send_message(from_user, response)
            
            return {"status": "success", "response": response}
            
        except Exception as e:
            error_msg = f"处理消息时出错: {str(e)}"
            print(f"❌ {error_msg}")
            
            # 发送错误提示
            self.send_message(from_user, "抱歉，系统暂时无法处理您的请求，请稍后再试。")
            
            return {"status": "error", "error": error_msg}
    
    def send_message(self, user_id: str, message: str) -> bool:
        """发送消息给用户"""
        try:
            self.wechat.message.send_text(
                agent_id=self.agent_id,
                user_ids=user_id,
                content=message
            )
            print(f"📤 消息已发送给 {user_id}: {message[:50]}...")
            return True
            
        except WeChatException as e:
            print(f"❌ 发送消息失败: {e}")
            return False
    
    def send_card_message(self, user_id: str, title: str, description: str, url: str = None) -> bool:
        """发送卡片消息"""
        try:
            card_data = {
                "title": title,
                "description": description,
                "url": url or "#",
                "btntxt": "查看详情"
            }
            
            self.wechat.message.send_textcard(
                agent_id=self.agent_id,
                user_ids=user_id,
                title=card_data["title"],
                description=card_data["description"],
                url=card_data["url"],
                btntxt=card_data["btntxt"]
            )
            
            print(f"📋 卡片消息已发送给 {user_id}: {title}")
            return True
            
        except WeChatException as e:
            print(f"❌ 发送卡片消息失败: {e}")
            return False
    
    def broadcast_message(self, message: str, users: list = None) -> bool:
        """群发消息"""
        try:
            if users:
                user_ids = "|".join(users)
            else:
                user_ids = "@all"  # 发送给所有人
            
            self.wechat.message.send_text(
                agent_id=self.agent_id,
                user_ids=user_ids,
                content=message
            )
            
            print(f"📢 群发消息完成: {message[:50]}...")
            return True
            
        except WeChatException as e:
            print(f"❌ 群发消息失败: {e}")
            return False
    
    def _get_user_by_wechat_id(self, wechat_userid: str) -> Optional[User]:
        """根据企业微信用户ID获取系统用户"""
        with get_db_context() as db:
            return db.query(User).filter(User.wechat_userid == wechat_userid).first()
    
    def _save_conversation(self, wechat_userid: str, user_message: str, 
                          ai_response: str, user: Optional[User], processing_time: float):
        """保存对话记录"""
        with get_db_context() as db:
            conversation = AIConversation(
                wechat_userid=wechat_userid,
                user_id=user.id if user else None,
                message_type="text",
                user_message=user_message,
                ai_response=ai_response,
                processing_time=processing_time,
                created_at=datetime.utcnow()
            )
            db.add(conversation)
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """获取企业微信用户信息"""
        try:
            user_info = self.wechat.user.get(user_id)
            return {
                "userid": user_info.get("userid"),
                "name": user_info.get("name"),
                "department": user_info.get("department"),
                "position": user_info.get("position"),
                "mobile": user_info.get("mobile"),
                "email": user_info.get("email")
            }
        except WeChatException as e:
            print(f"❌ 获取用户信息失败: {e}")
            return {}
    
    def send_reminder(self, user_id: str, title: str, content: str, project_id: int = None) -> bool:
        """发送提醒消息"""
        try:
            reminder_text = f"📋 {title}\n\n{content}"
            
            if project_id:
                reminder_text += f"\n\n项目编号: {project_id}"
                reminder_text += f"\n回复 '查询 {project_id}' 查看详情"
            
            return self.send_message(user_id, reminder_text)
            
        except Exception as e:
            print(f"❌ 发送提醒失败: {e}")
            return False

# 全局机器人实例
_bot_instance = None

def get_wechat_bot() -> WeChatBot:
    """获取企业微信机器人实例 (单例模式)"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = WeChatBot()
    return _bot_instance

def init_wechat_bot() -> bool:
    """初始化企业微信机器人"""
    try:
        bot = get_wechat_bot()
        print("✅ 企业微信机器人初始化成功")
        return True
    except Exception as e:
        print(f"❌ 企业微信机器人初始化失败: {e}")
        return False