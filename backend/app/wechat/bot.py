#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 企业微信机器人核心（更新版）
处理企业微信消息的核心逻辑，集成完整的MessageHandler
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
from app.wechat.handlers import MessageHandler  # 🔥 这里调用了新的handlers
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
        
        # 🔥 重要：这里创建了新的消息处理器
        self.message_handler = MessageHandler()
        
        self.utils = WeChatUtils()
        
        print("✅ 企业微信机器人初始化完成")
    
    async def handle_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理接收到的消息 - 主入口"""
        start_time = time.time()
        
        try:
            # 提取消息基本信息
            msg_type = data.get('MsgType', 'text')
            from_user = data.get('FromUserName', '')
            
            print(f"📨 收到消息: 用户={from_user}, 类型={msg_type}")
            
            # 获取用户信息
            user = self._get_user_by_wechat_id(from_user)
            if user:
                print(f"👤 用户已绑定: {user.username} ({user.role})")
            else:
                print(f"⚠️ 用户未绑定: {from_user}")
            
            # 🔥 关键：根据消息类型调用不同的处理方法
            response = ""
            if msg_type == 'text':
                content = data.get('Content', '')
                print(f"📝 文本消息: {content[:100]}...")
                response = await self.message_handler.handle_text_message(
                    content, from_user, user
                )
                
            elif msg_type == 'image':
                print(f"📷 图片消息: MediaId={data.get('MediaId', '')}")
                response = await self.message_handler.handle_image_message(
                    data, from_user, user
                )
                
            elif msg_type == 'file':
                print(f"📎 文件消息: {data.get('Title', '未知文件')}")
                response = await self.message_handler.handle_file_message(
                    data, from_user, user
                )
                
            elif msg_type == 'voice':
                # 语音消息转为文本处理
                content = data.get('Recognition', '') or "语音消息"
                print(f"🎤 语音消息: {content}")
                response = await self.message_handler.handle_text_message(
                    content, from_user, user
                )
                
            else:
                response = f"抱歉，暂不支持 {msg_type} 类型的消息。\n\n💡 支持：文字、图片、文件、语音"
            
            # 记录对话历史
            processing_time = time.time() - start_time
            await self._save_conversation(from_user, data, response, user, processing_time)
            
            # 发送回复
            success = await self.send_message(from_user, response)
            
            print(f"✅ 消息处理完成，耗时: {processing_time:.2f}秒")
            
            return {
                "status": "success", 
                "response": response,
                "processing_time": processing_time,
                "sent": success
            }
            
        except Exception as e:
            error_msg = f"处理消息时出错: {str(e)}"
            print(f"❌ {error_msg}")
            
            # 发送友好的错误提示
            await self.send_message(from_user, 
                "抱歉，系统暂时无法处理您的请求，请稍后再试。\n\n如问题持续，请联系管理员。")
            
            return {"status": "error", "error": error_msg}
    
    async def send_message(self, user_id: str, message: str) -> bool:
        """发送消息给用户"""
        try:
            # 限制消息长度，微信有字符限制
            if len(message) > 2000:
                message = message[:1950] + "\n\n...(消息过长，已截断)\n💡 详情请访问Web管理界面"
            
            self.wechat.message.send_text(
                agent_id=self.agent_id,
                user_ids=user_id,
                content=message
            )
            print(f"📤 消息已发送给 {user_id}: {len(message)}字符")
            return True
            
        except WeChatException as e:
            print(f"❌ 发送消息失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 发送消息异常: {e}")
            return False
    
    async def send_card_message(self, user_id: str, title: str, description: str, url: str = None) -> bool:
        """发送卡片消息"""
        try:
            self.wechat.message.send_textcard(
                agent_id=self.agent_id,
                user_ids=user_id,
                title=title,
                description=description,
                url=url or "#",
                btntxt="查看详情"
            )
            
            print(f"📋 卡片消息已发送给 {user_id}: {title}")
            return True
            
        except WeChatException as e:
            print(f"❌ 发送卡片消息失败: {e}")
            return False
    
    async def broadcast_message(self, message: str, users: list = None) -> bool:
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
            
            recipient_count = len(users) if users else "所有用户"
            print(f"📢 群发消息完成: 发送给 {recipient_count}")
            return True
            
        except WeChatException as e:
            print(f"❌ 群发消息失败: {e}")
            return False
    
    def _get_user_by_wechat_id(self, wechat_userid: str) -> Optional[User]:
        """根据企业微信用户ID获取系统用户"""
        try:
            with get_db_context() as db:
                return db.query(User).filter(User.wechat_userid == wechat_userid).first()
        except Exception as e:
            print(f"❌ 查询用户失败: {e}")
            return None
    
    async def _save_conversation(
        self, 
        wechat_userid: str, 
        message_data: Dict[str, Any],
        ai_response: str, 
        user: Optional[User], 
        processing_time: float
    ):
        """保存对话记录"""
        try:
            with get_db_context() as db:
                # 提取用户消息内容
                msg_type = message_data.get('MsgType', 'text')
                if msg_type == 'text':
                    user_message = message_data.get('Content', '')
                elif msg_type == 'image':
                    user_message = f"[图片消息] MediaId: {message_data.get('MediaId', '')}"
                elif msg_type == 'file':
                    user_message = f"[文件消息] {message_data.get('Title', '未知文件')}"
                elif msg_type == 'voice':
                    user_message = f"[语音消息] {message_data.get('Recognition', '')}"
                else:
                    user_message = f"[{msg_type}消息]"
                
                conversation = AIConversation(
                    wechat_userid=wechat_userid,
                    user_id=user.id if user else None,
                    message_type=msg_type,
                    user_message=user_message,
                    ai_response=ai_response,
                    processing_time=processing_time,
                    created_at=datetime.utcnow()
                )
                db.add(conversation)
                # get_db_context 会自动commit
                
        except Exception as e:
            print(f"❌ 保存对话记录失败: {e}")
    
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
                "email": user_info.get("email"),
                "avatar": user_info.get("avatar")
            }
        except WeChatException as e:
            print(f"❌ 获取用户信息失败: {e}")
            return {}
    
    async def send_reminder(self, user_id: str, title: str, content: str, project_id: int = None) -> bool:
        """发送提醒消息"""
        try:
            reminder_text = f"📋 {title}\n\n{content}"
            
            if project_id:
                reminder_text += f"\n\n🆔 项目编号: {project_id}"
                reminder_text += f"\n💡 回复 '查询 {project_id}' 查看详情"
            
            return await self.send_message(user_id, reminder_text)
            
        except Exception as e:
            print(f"❌ 发送提醒失败: {e}")
            return False
    
    async def handle_menu_click(self, event_key: str, user_id: str) -> bool:
        """处理菜单点击事件"""
        try:
            user = self._get_user_by_wechat_id(user_id)
            
            menu_responses = {
                "my_projects": "我的项目",
                "create_project": "创建",
                "statistics": "统计",
                "suppliers": "供应商",
                "help": "帮助"
            }
            
            if event_key in menu_responses:
                # 模拟用户发送指令
                response = await self.message_handler.handle_text_message(
                    menu_responses[event_key], user_id, user
                )
                return await self.send_message(user_id, response)
            
            return False
            
        except Exception as e:
            print(f"❌ 处理菜单点击失败: {e}")
            return False
    
    def get_bot_status(self) -> Dict[str, Any]:
        """获取机器人状态"""
        try:
            # 测试API连接
            token = self.wechat.access_token
            status = "online" if token else "offline"
            
            return {
                "status": status,
                "corp_id": self.corp_id[:8] + "***",  # 隐藏敏感信息
                "agent_id": self.agent_id,
                "handlers_loaded": bool(self.message_handler),
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

# 全局机器人实例
_bot_instance = None

def get_wechat_bot() -> WeChatBot:
    """获取企业微信机器人实例 (单例模式)"""
    global _bot_instance
    if _bot_instance is None:
        try:
            _bot_instance = WeChatBot()
            print("✅ 企业微信机器人实例创建成功")
        except Exception as e:
            print(f"❌ 企业微信机器人创建失败: {e}")
            _bot_instance = None
    return _bot_instance

def init_wechat_bot() -> bool:
    """初始化企业微信机器人"""
    try:
        bot = get_wechat_bot()
        if bot:
            print("✅ 企业微信机器人初始化成功")
            return True
        else:
            print("❌ 企业微信机器人初始化失败")
            return False
    except Exception as e:
        print(f"❌ 企业微信机器人初始化异常: {e}")
        return False

# 🔥 测试函数 - 方便调试
async def test_message_handling():
    """测试消息处理功能"""
    print("🧪 测试企业微信消息处理...")
    
    try:
        bot = get_wechat_bot()
        if not bot:
            print("❌ 机器人未初始化")
            return
        
        # 模拟文本消息
        test_data = {
            'MsgType': 'text',
            'FromUserName': 'test_user',
            'Content': '帮助'
        }
        
        result = await bot.handle_message(test_data)
        print(f"✅ 测试结果: {result}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    """直接运行时的测试"""
    import asyncio
    
    print("🤖 企业微信机器人测试")
    print("=" * 50)
    
    # 初始化测试
    if init_wechat_bot():
        # 异步测试
        asyncio.run(test_message_handling())
    
    print("=" * 50)