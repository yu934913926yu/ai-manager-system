#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 企业微信工具函数
提供企业微信API调用和工具函数
"""

import hashlib
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from wechatpy.enterprise import WeChatEnterprise
from wechatpy.exceptions import WeChatException
from app.config import get_settings

settings = get_settings()

class WeChatUtils:
    """企业微信工具类"""
    
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.secret = settings.WECHAT_CORP_SECRET
        self.agent_id = settings.WECHAT_AGENT_ID
        
        if all([self.corp_id, self.secret]):
            self.wechat = WeChatEnterprise(self.corp_id, self.secret)
        else:
            self.wechat = None
            print("⚠️ 企业微信配置不完整")
    
    def verify_url(self, signature: str, timestamp: str, nonce: str, echo_str: str) -> Optional[str]:
        """验证URL有效性"""
        if not self.wechat:
            return None
        
        try:
            # 企业微信URL验证逻辑
            token = "your_verify_token"  # 需要在企业微信后台配置
            tmp_arr = [token, timestamp, nonce]
            tmp_arr.sort()
            tmp_str = ''.join(tmp_arr)
            tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
            
            if tmp_str == signature:
                return echo_str
            else:
                return None
                
        except Exception as e:
            print(f"❌ URL验证失败: {e}")
            return None
    
    def get_access_token(self) -> Optional[str]:
        """获取企业微信访问令牌"""
        if not self.wechat:
            return None
        
        try:
            token_info = self.wechat.access_token
            return token_info
        except WeChatException as e:
            print(f"❌ 获取访问令牌失败: {e}")
            return None
    
    def get_user_list(self, department_id: int = 1) -> List[Dict[str, Any]]:
        """获取部门用户列表"""
        if not self.wechat:
            return []
        
        try:
            users = self.wechat.user.list(department_id)
            return users.get("userlist", [])
        except WeChatException as e:
            print(f"❌ 获取用户列表失败: {e}")
            return []
    
    def get_user_detail(self, user_id: str) -> Dict[str, Any]:
        """获取用户详细信息"""
        if not self.wechat:
            return {}
        
        try:
            user_info = self.wechat.user.get(user_id)
            return {
                "userid": user_info.get("userid"),
                "name": user_info.get("name"),
                "department": user_info.get("department"),
                "position": user_info.get("position"),
                "mobile": user_info.get("mobile"),
                "email": user_info.get("email"),
                "avatar": user_info.get("avatar"),
                "status": user_info.get("status")
            }
        except WeChatException as e:
            print(f"❌ 获取用户详情失败: {e}")
            return {}
    
    def download_media(self, media_id: str) -> Optional[bytes]:
        """下载媒体文件"""
        if not self.wechat:
            return None
        
        try:
            media_data = self.wechat.media.download(media_id)
            return media_data
        except WeChatException as e:
            print(f"❌ 下载媒体文件失败: {e}")
            return None
    
    def upload_media(self, media_type: str, media_file) -> Optional[str]:
        """上传媒体文件"""
        if not self.wechat:
            return None
        
        try:
            result = self.wechat.media.upload(media_type, media_file)
            return result.get("media_id")
        except WeChatException as e:
            print(f"❌ 上传媒体文件失败: {e}")
            return None
    
    def create_menu(self, menu_data: Dict[str, Any]) -> bool:
        """创建应用菜单"""
        if not self.wechat:
            return False
        
        try:
            self.wechat.menu.create(self.agent_id, menu_data)
            print("✅ 应用菜单创建成功")
            return True
        except WeChatException as e:
            print(f"❌ 创建应用菜单失败: {e}")
            return False
    
    def send_notification(self, user_ids: List[str], title: str, content: str) -> bool:
        """发送通知消息"""
        if not self.wechat:
            return False
        
        try:
            user_id_str = "|".join(user_ids)
            message = f"📢 {title}\n\n{content}"
            
            self.wechat.message.send_text(
                agent_id=self.agent_id,
                user_ids=user_id_str,
                content=message
            )
            
            print(f"📤 通知已发送给 {len(user_ids)} 位用户")
            return True
            
        except WeChatException as e:
            print(f"❌ 发送通知失败: {e}")
            return False
    
    def format_project_card(self, project_data: Dict[str, Any]) -> str:
        """格式化项目信息卡片"""
        template = """📋 项目信息卡片

🆔 项目编号：{project_number}
👤 客户：{customer_name}
📝 项目：{project_name}
📊 状态：{status}
💰 金额：{amount}
📅 创建：{created_at}

点击查看详情 →"""
        
        return template.format(
            project_number=project_data.get("project_number", "未知"),
            customer_name=project_data.get("customer_name", "未知"),
            project_name=project_data.get("project_name", "未知"),
            status=project_data.get("status", "未知"),
            amount=project_data.get("quoted_price", "未报价"),
            created_at=project_data.get("created_at", "未知")
        )
    
    def validate_wechat_config(self) -> bool:
        """验证企业微信配置"""
        if not all([self.corp_id, self.secret, self.agent_id]):
            print("❌ 企业微信配置不完整")
            return False
        
        try:
            # 尝试获取访问令牌
            token = self.get_access_token()
            if token:
                print("✅ 企业微信配置验证成功")
                return True
            else:
                print("❌ 企业微信配置验证失败")
                return False
                
        except Exception as e:
            print(f"❌ 企业微信配置验证异常: {e}")
            return False
    
    def get_callback_url_config(self, callback_url: str) -> Dict[str, str]:
        """获取回调URL配置信息"""
        return {
            "url": callback_url,
            "token": "your_callback_token",
            "encoding_aes_key": "your_encoding_aes_key",
            "corp_id": self.corp_id
        }
    
    def parse_wechat_message(self, xml_data: str) -> Dict[str, Any]:
        """解析企业微信消息XML"""
        try:
            # 这里应该使用wechatpy的消息解析功能
            # 简化实现，实际应该根据XML结构解析
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_data)
            message_data = {}
            
            for child in root:
                message_data[child.tag] = child.text
            
            return message_data
            
        except Exception as e:
            print(f"❌ 解析微信消息失败: {e}")
            return {}
    
    def generate_signature(self, timestamp: str, nonce: str, token: str) -> str:
        """生成签名"""
        try:
            tmp_arr = [token, timestamp, nonce]
            tmp_arr.sort()
            tmp_str = ''.join(tmp_arr)
            return hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        except Exception as e:
            print(f"❌ 生成签名失败: {e}")
            return ""

# 工具函数
def init_default_menu() -> Dict[str, Any]:
    """初始化默认菜单"""
    return {
        "button": [
            {
                "type": "click",
                "name": "我的项目", 
                "key": "my_projects"
            },
            {
                "type": "click",
                "name": "创建项目",
                "key": "create_project"
            },
            {
                "name": "更多功能",
                "sub_button": [
                    {
                        "type": "click",
                        "name": "项目统计",
                        "key": "statistics"
                    },
                    {
                        "type": "click", 
                        "name": "供应商",
                        "key": "suppliers"
                    },
                    {
                        "type": "click",
                        "name": "帮助",
                        "key": "help"
                    }
                ]
            }
        ]
    }

def format_reminder_message(reminder_type: str, data: Dict[str, Any]) -> str:
    """格式化提醒消息"""
    templates = {
        "project_deadline": "⏰ 项目截止提醒\n\n项目：{project_name}\n客户：{customer_name}\n截止时间：{deadline}\n\n请及时跟进项目进度！",
        "payment_reminder": "💰 收款提醒\n\n项目：{project_name}\n金额：{amount}\n类型：{payment_type}\n\n请确认收款状态！",
        "status_change": "📊 项目状态变更\n\n项目：{project_name}\n状态：{old_status} → {new_status}\n变更人：{changer}\n\n请关注项目进展！"
    }
    
    template = templates.get(reminder_type, "📢 系统提醒\n\n{content}")
    return template.format(**data)

# 测试函数
def test_wechat_utils():
    """测试企业微信工具函数"""
    print("🔧 企业微信工具测试")
    print("=" * 40)
    
    utils = WeChatUtils()
    
    # 测试配置验证
    config_valid = utils.validate_wechat_config()
    print(f"配置验证: {'✅' if config_valid else '❌'}")
    
    # 测试菜单数据
    menu_data = init_default_menu()
    print(f"默认菜单: {'✅' if menu_data.get('button') else '❌'}")
    
    print("=" * 40)

if __name__ == "__main__":
    test_wechat_utils()