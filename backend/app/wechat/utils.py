#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 企业微信工具类
封装企业微信API调用的通用方法
"""

import json
import time
import hashlib
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from wechatpy import WeChatClient
from wechatpy.enterprise import WeChatClient as WeChatEnterpriseClient
from wechatpy.exceptions import WeChatException

from app.config import get_settings

settings = get_settings()

class WeChatUtils:
    """企业微信工具类"""
    
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.corp_secret = settings.WECHAT_CORP_SECRET
        self.agent_id = settings.WECHAT_AGENT_ID
        
        # 初始化企业微信客户端
        if self.corp_id and self.corp_secret:
            self.client = WeChatEnterpriseClient(
                self.corp_id,
                self.corp_secret
            )
        else:
            self.client = None
            print("⚠️ 企业微信配置不完整")
        
        # Token缓存
        self._access_token = None
        self._token_expires_at = None
    
    def get_access_token(self) -> Optional[str]:
        """获取企业微信access_token"""
        if not self.client:
            return None
        
        # 检查缓存
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        try:
            # 获取新token
            token_data = self.client.access_token
            self._access_token = token_data
            # 设置过期时间（提前5分钟）
            self._token_expires_at = datetime.now() + timedelta(seconds=7200 - 300)
            return self._access_token
            
        except Exception as e:
            print(f"❌ 获取access_token失败: {e}")
            return None
    
    def send_text_message(self, user_id: str, content: str) -> bool:
        """发送文本消息"""
        if not self.client:
            return False
        
        try:
            self.client.message.send_text(
                agent_id=self.agent_id,
                user_ids=user_id,
                content=content
            )
            return True
            
        except WeChatException as e:
            print(f"❌ 发送消息失败: {e}")
            return False
    
    def send_markdown_message(self, user_id: str, content: str) -> bool:
        """发送Markdown消息"""
        if not self.client:
            return False
        
        try:
            self.client.message.send_markdown(
                agent_id=self.agent_id,
                user_ids=user_id,
                content=content
            )
            return True
            
        except WeChatException as e:
            print(f"❌ 发送Markdown消息失败: {e}")
            return False
    
    def send_card_message(self, user_id: str, card_data: Dict[str, Any]) -> bool:
        """发送卡片消息"""
        if not self.client:
            return False
        
        try:
            self.client.message.send_text_card(
                agent_id=self.agent_id,
                user_ids=user_id,
                title=card_data.get('title', ''),
                description=card_data.get('description', ''),
                url=card_data.get('url', ''),
                btntxt=card_data.get('btntxt', '详情')
            )
            return True
            
        except WeChatException as e:
            print(f"❌ 发送卡片消息失败: {e}")
            return False
    
    def send_image(self, user_id: str, media_id: str) -> bool:
        """发送图片消息"""
        if not self.client:
            return False
        
        try:
            self.client.message.send_image(
                agent_id=self.agent_id,
                user_ids=user_id,
                media_id=media_id
            )
            return True
            
        except WeChatException as e:
            print(f"❌ 发送图片失败: {e}")
            return False
    
    def send_file(self, user_id: str, media_id: str) -> bool:
        """发送文件消息"""
        if not self.client:
            return False
        
        try:
            self.client.message.send_file(
                agent_id=self.agent_id,
                user_ids=user_id,
                media_id=media_id
            )
            return True
            
        except WeChatException as e:
            print(f"❌ 发送文件失败: {e}")
            return False
    
    def send_template_card(self, user_id: str, template_card: Dict[str, Any]) -> bool:
        """发送模板卡片消息"""
        if not self.client:
            return False
        
        try:
            # 构建请求数据
            data = {
                "touser": user_id,
                "msgtype": "template_card",
                "agentid": self.agent_id,
                "template_card": template_card
            }
            
            # 发送请求
            token = self.get_access_token()
            if not token:
                return False
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get('errcode') == 0:
                return True
            else:
                print(f"❌ 发送模板卡片失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送模板卡片异常: {e}")
            return False
    
    def download_media(self, media_id: str) -> Optional[bytes]:
        """下载媒体文件"""
        if not self.client:
            return None
        
        try:
            # 获取access_token
            token = self.get_access_token()
            if not token:
                return None
            
            # 下载文件
            url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={token}&media_id={media_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                # 检查是否是错误响应
                try:
                    error_data = response.json()
                    if 'errcode' in error_data:
                        print(f"❌ 下载媒体文件失败: {error_data}")
                        return None
                except:
                    # 不是JSON，说明是文件内容
                    return response.content
            
            return None
            
        except Exception as e:
            print(f"❌ 下载媒体文件异常: {e}")
            return None
    
    def upload_media(self, media_type: str, media_file: bytes, filename: str) -> Optional[str]:
        """上传媒体文件"""
        if not self.client:
            return None
        
        try:
            # 上传文件
            result = self.client.media.upload(media_type, media_file)
            return result.get('media_id')
            
        except WeChatException as e:
            print(f"❌ 上传媒体文件失败: {e}")
            return None
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        if not self.client:
            return None
        
        try:
            user_info = self.client.user.get(user_id)
            return user_info
            
        except WeChatException as e:
            print(f"❌ 获取用户信息失败: {e}")
            return None
    
    def get_department_users(self, department_id: int) -> List[Dict[str, Any]]:
        """获取部门成员列表"""
        if not self.client:
            return []
        
        try:
            users = self.client.user.list(department_id, fetch_child=True)
            return users
            
        except WeChatException as e:
            print(f"❌ 获取部门成员失败: {e}")
            return []
    
    def create_group_chat(self, name: str, owner: str, userlist: List[str]) -> Optional[str]:
        """创建群聊"""
        if not self.client:
            return None
        
        try:
            # 调用API创建群聊
            token = self.get_access_token()
            if not token:
                return None
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/appchat/create?access_token={token}"
            data = {
                "name": name,
                "owner": owner,
                "userlist": userlist,
                "chatid": f"chat_{int(time.time())}"
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get('errcode') == 0:
                return result.get('chatid')
            else:
                print(f"❌ 创建群聊失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 创建群聊异常: {e}")
            return None
    
    def send_group_message(self, chat_id: str, content: str) -> bool:
        """发送群聊消息"""
        if not self.client:
            return False
        
        try:
            # 发送群聊文本消息
            token = self.get_access_token()
            if not token:
                return False
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/appchat/send?access_token={token}"
            data = {
                "chatid": chat_id,
                "msgtype": "text",
                "text": {
                    "content": content
                },
                "safe": 0
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get('errcode') == 0:
                return True
            else:
                print(f"❌ 发送群聊消息失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送群聊消息异常: {e}")
            return False
    
    def verify_callback_signature(self, signature: str, timestamp: str, nonce: str, echostr: str = None) -> bool:
        """验证回调签名"""
        # 这里需要配置回调Token
        token = settings.WECHAT_CALLBACK_TOKEN
        if not token:
            return False
        
        # 将token、timestamp、nonce按字典序排序
        tmp_list = [token, timestamp, nonce]
        if echostr:
            tmp_list.append(echostr)
        tmp_list.sort()
        
        # 拼接并SHA1加密
        tmp_str = ''.join(tmp_list)
        tmp_str = hashlib.sha1(tmp_str.encode()).hexdigest()
        
        # 比较签名
        return tmp_str == signature
    
    def format_project_card(self, project: Any) -> Dict[str, Any]:
        """格式化项目卡片消息"""
        return {
            "card_type": "text_notice",
            "source": {
                "icon_url": "https://example.com/icon.png",
                "desc": "AI项目管理系统"
            },
            "main_title": {
                "title": f"项目：{project.project_name}",
                "desc": f"客户：{project.customer_name}"
            },
            "emphasis_content": {
                "title": "项目状态",
                "desc": project.status
            },
            "sub_title_text": f"项目编号：{project.project_number}",
            "horizontal_content_list": [
                {
                    "keyname": "负责人",
                    "value": project.designer.full_name if project.designer else "未分配"
                },
                {
                    "keyname": "截止日期",
                    "value": project.deadline.strftime('%Y-%m-%d') if project.deadline else "未设定"
                }
            ],
            "jump_list": [
                {
                    "type": 1,
                    "title": "查看详情",
                    "url": f"{settings.FRONTEND_URL}/projects/{project.id}"
                }
            ],
            "card_action": {
                "type": 1,
                "url": f"{settings.FRONTEND_URL}/projects/{project.id}"
            }
        }

# 全局实例
_wechat_utils = None

def get_wechat_utils() -> WeChatUtils:
    """获取企业微信工具实例"""
    global _wechat_utils
    if _wechat_utils is None:
        _wechat_utils = WeChatUtils()
    return _wechat_utils