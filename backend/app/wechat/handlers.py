#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 企业微信消息处理器
处理各种类型的消息和指令
"""

import re
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date

from sqlalchemy.orm import Session
from app.database import get_db_context
from app.models import User, Project, Task, Supplier
from app.wechat.utils import WeChatUtils
from app import StatusEnum

class MessageHandler:
    """消息处理器"""
    
    def __init__(self):
        self.utils = WeChatUtils()
        self.commands = {
            "帮助": self.handle_help,
            "help": self.handle_help,
            "创建": self.handle_create_project,
            "查询": self.handle_query_project,
            "更新": self.handle_update_status,
            "状态": self.handle_status_update,
            "我的": self.handle_my_projects,
            "统计": self.handle_statistics,
            "供应商": self.handle_supplier_query
        }
    
    def handle_text_message(self, content: str, wechat_userid: str, user: Optional[User]) -> str:
        """处理文本消息"""
        content = content.strip()
        
        # 检查用户是否绑定
        if not user:
            return self._handle_unbound_user(content, wechat_userid)
        
        # 处理@机器人的消息
        if content.startswith("@AI总管"):
            content = content.replace("@AI总管", "").strip()
        
        # 空消息处理
        if not content:
            return "您好！我是AI运营总管，输入'帮助'查看可用指令。"
        
        # 命令匹配
        for keyword, handler in self.commands.items():
            if content.startswith(keyword):
                params = content[len(keyword):].strip()
                return handler(params, user)
        
        # 智能识别项目信息 (OCR后的文本)
        if self._is_project_info(content):
            return self.handle_ocr_project_creation(content, user)
        
        # 默认智能问答
        return self.handle_smart_qa(content, user)
    
    def handle_image_message(self, data: Dict[str, Any], wechat_userid: str, user: Optional[User]) -> str:
        """处理图片消息"""
        if not user:
            return "请先完成账户绑定后再上传图片。"
        
        try:
            # 这里后续会集成OCR功能
            media_id = data.get('MediaId', '')
            
            # 模拟OCR识别结果
            ocr_result = self._simulate_ocr_result()
            
            if ocr_result:
                return f"📷 图片识别完成：\n\n{ocr_result}\n\n请确认信息是否正确，回复'确认'创建项目。"
            else:
                return "抱歉，无法识别图片中的项目信息，请尝试重新拍照或手动输入。"
                
        except Exception as e:
            return f"图片处理失败：{str(e)}"
    
    def handle_file_message(self, data: Dict[str, Any], wechat_userid: str, user: Optional[User]) -> str:
        """处理文件消息"""
        if not user:
            return "请先完成账户绑定后再上传文件。"
        
        filename = data.get('Title', '未知文件')
        return f"📎 已收到文件：{filename}\n\n文件已保存，可通过Web管理界面查看详情。"
    
    def handle_help(self, params: str, user: User) -> str:
        """处理帮助指令"""
        help_text = """🤖 AI运营总管指令帮助

📋 **项目管理**
- 创建 [项目信息] - 创建新项目
- 查询 [项目编号] - 查询项目详情
- 更新 [项目编号] [状态] - 更新项目状态
- 我的项目 - 查看我负责的项目

📊 **数据统计**
- 统计 - 查看项目统计信息
- 供应商 [类型] - 查询供应商信息

💡 **使用技巧**
- 直接拍照笔记本，AI会自动识别项目信息
- 支持语音转文字输入
- 回复'确认'完成项目创建

❓ 遇到问题请联系管理员"""
        return help_text
    
    def handle_create_project(self, params: str, user: User) -> str:
        """处理创建项目指令"""
        if not params:
            return "请提供项目信息，格式：创建 客户名称 项目名称 报价金额"
        
        try:
            # 解析参数
            parts = params.split()
            if len(parts) < 2:
                return "项目信息不完整，请提供至少客户名称和项目名称。"
            
            customer_name = parts[0]
            project_name = " ".join(parts[1:-1]) if len(parts) > 2 else parts[1]
            quoted_price = None
            
            # 尝试解析价格
            if len(parts) > 2 and self._is_number(parts[-1]):
                quoted_price = float(parts[-1])
                project_name = " ".join(parts[1:-1])
            
            # 创建项目
            with get_db_context() as db:
                project_count = db.query(Project).count()
                project_number = f"PRJ{datetime.now().strftime('%Y%m%d')}{project_count + 1:03d}"
                
                project = Project(
                    project_number=project_number,
                    project_name=project_name,
                    customer_name=customer_name,
                    quoted_price=quoted_price,
                    creator_id=user.id,
                    status=StatusEnum.PENDING_QUOTE,
                    created_at=datetime.utcnow()
                )
                
                db.add(project)
                db.commit()
                
                return f"✅ 项目创建成功！\n\n项目编号：{project_number}\n客户：{customer_name}\n项目：{project_name}\n状态：{StatusEnum.PENDING_QUOTE}"
                
        except Exception as e:
            return f"❌ 项目创建失败：{str(e)}"
    
    def handle_query_project(self, params: str, user: User) -> str:
        """处理查询项目指令"""
        if not params:
            return "请提供项目编号，格式：查询 PRJ20240101001"
        
        project_number = params.strip()
        
        with get_db_context() as db:
            project = db.query(Project).filter(
                Project.project_number == project_number
            ).first()
            
            if not project:
                return f"❌ 未找到项目编号：{project_number}"
            
            # 权限检查
            if not self._can_access_project(user, project):
                return "❌ 您没有权限查看此项目"
            
            # 构建项目信息
            info = f"""📋 项目详情

🆔 项目编号：{project.project_number}
👤 客户：{project.customer_name}
📝 项目：{project.project_name}
📊 状态：{project.status}
💰 报价：{project.quoted_price or '未报价'}
📅 创建时间：{project.created_at.strftime('%Y-%m-%d %H:%M')}
"""
            
            if project.deadline:
                info += f"⏰ 截止时间：{project.deadline}\n"
            
            if project.notes:
                info += f"📝 备注：{project.notes}\n"
            
            return info
    
    def handle_update_status(self, params: str, user: User) -> str:
        """处理状态更新指令"""
        parts = params.split(maxsplit=1)
        if len(parts) < 2:
            return "请提供项目编号和新状态，格式：更新 PRJ20240101001 设计中"
        
        project_number, new_status = parts
        
        # 状态映射
        status_mapping = {
            "待报价": StatusEnum.PENDING_QUOTE,
            "已报价": StatusEnum.QUOTED,
            "客户确认": StatusEnum.CONFIRMED,
            "定金已付": StatusEnum.DEPOSIT_PAID,
            "设计中": StatusEnum.IN_DESIGN,
            "待客户确认": StatusEnum.PENDING_APPROVAL,
            "客户定稿": StatusEnum.APPROVED,
            "生产中": StatusEnum.IN_PRODUCTION,
            "项目完成": StatusEnum.COMPLETED,
            "尾款已付": StatusEnum.PAID
        }
        
        if new_status not in status_mapping:
            available_statuses = "、".join(status_mapping.keys())
            return f"❌ 无效状态，可用状态：{available_statuses}"
        
        with get_db_context() as db:
            project = db.query(Project).filter(
                Project.project_number == project_number
            ).first()
            
            if not project:
                return f"❌ 未找到项目编号：{project_number}"
            
            if not self._can_modify_project(user, project):
                return "❌ 您没有权限修改此项目"
            
            old_status = project.status
            project.status = status_mapping[new_status]
            project.updated_at = datetime.utcnow()
            
            return f"✅ 项目状态更新成功！\n\n{project_number}\n{old_status} → {new_status}"
    
    def handle_my_projects(self, params: str, user: User) -> str:
        """处理我的项目指令"""
        with get_db_context() as db:
            projects = db.query(Project).filter(
                (Project.creator_id == user.id) | (Project.designer_id == user.id)
            ).order_by(Project.created_at.desc()).limit(10).all()
            
            if not projects:
                return "📋 您暂时没有相关项目"
            
            result = "📋 我的项目列表：\n\n"
            for project in projects:
                result += f"🆔 {project.project_number}\n"
                result += f"👤 {project.customer_name} - {project.project_name}\n"
                result += f"📊 {project.status}\n"
                result += "---\n"
            
            return result
    
    def handle_statistics(self, params: str, user: User) -> str:
        """处理统计信息指令"""
        with get_db_context() as db:
            # 基础统计
            total_projects = db.query(Project).count()
            my_projects = db.query(Project).filter(
                (Project.creator_id == user.id) | (Project.designer_id == user.id)
            ).count()
            
            # 状态统计
            in_progress = db.query(Project).filter(
                Project.status.in_([StatusEnum.IN_DESIGN, StatusEnum.IN_PRODUCTION])
            ).count()
            
            completed = db.query(Project).filter(
                Project.status == StatusEnum.COMPLETED
            ).count()
            
            return f"""📊 项目统计信息

🏢 公司总项目：{total_projects}
👤 我的项目：{my_projects}
🔄 进行中：{in_progress}
✅ 已完成：{completed}

📅 统计时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"""
    
    def handle_supplier_query(self, params: str, user: User) -> str:
        """处理供应商查询指令"""
        with get_db_context() as db:
            if params:
                # 按类型查询
                suppliers = db.query(Supplier).filter(
                    Supplier.service_type.like(f"%{params}%")
                ).order_by(Supplier.rating.desc()).limit(5).all()
                
                if not suppliers:
                    return f"❌ 未找到'{params}'类型的供应商"
                
                result = f"🏢 {params}类供应商推荐：\n\n"
                for supplier in suppliers:
                    result += f"🏭 {supplier.name}\n"
                    result += f"📞 {supplier.phone or '未提供'}\n"
                    result += f"⭐ 评分：{supplier.rating}/10\n"
                    result += "---\n"
                
                return result
            else:
                # 显示供应商类型
                service_types = db.query(Supplier.service_type).distinct().all()
                types_list = [t[0] for t in service_types if t[0]]
                
                return f"🏢 可查询的供应商类型：\n\n" + "、".join(types_list)
    
    def handle_ocr_project_creation(self, content: str, user: User) -> str:
        """处理OCR识别的项目创建"""
        # 解析OCR识别的文本
        project_info = self._parse_ocr_content(content)
        
        if not project_info.get("customer_name"):
            return "❌ 无法识别客户信息，请手动输入项目信息。"
        
        return f"""📋 识别到项目信息：

👤 客户：{project_info.get('customer_name', '未识别')}
📝 项目：{project_info.get('project_name', '未识别')}
💰 金额：{project_info.get('amount', '未识别')}
📞 电话：{project_info.get('phone', '未识别')}

回复'确认'创建项目，回复'取消'重新输入"""
    
    def handle_smart_qa(self, content: str, user: User) -> str:
        """智能问答处理"""
        # 简单的关键词匹配
        if "项目" in content and "多少" in content:
            with get_db_context() as db:
                count = db.query(Project).filter(
                    (Project.creator_id == user.id) | (Project.designer_id == user.id)
                ).count()
                return f"您目前有 {count} 个相关项目。"
        
        if "怎么" in content or "如何" in content:
            return "您可以：\n1. 拍照笔记本让我识别项目信息\n2. 输入'创建'指令手动创建项目\n3. 输入'帮助'查看更多指令"
        
        return "抱歉，我不太理解您的问题。输入'帮助'查看可用指令，或直接描述您要执行的操作。"
    
    # 辅助方法
    def _handle_unbound_user(self, content: str, wechat_userid: str) -> str:
        """处理未绑定用户"""
        return """👋 欢迎使用AI运营总管！

您的企业微信账号尚未绑定系统账户，请联系管理员完成绑定后再使用。

🔗 绑定后您可以：
- 拍照创建项目
- 查询项目状态  
- 接收自动提醒
- 统计分析数据"""
    
    def _is_project_info(self, content: str) -> bool:
        """判断是否为项目信息"""
        keywords = ["客户", "项目", "金额", "电话", "公司", "设计"]
        return sum(1 for kw in keywords if kw in content) >= 2
    
    def _simulate_ocr_result(self) -> str:
        """模拟OCR识别结果"""
        return """客户：张三公司
项目：品牌LOGO设计
金额：5000元
电话：138-0000-0001
备注：需要3个方案"""
    
    def _parse_ocr_content(self, content: str) -> Dict[str, str]:
        """解析OCR识别的内容"""
        result = {}
        
        # 简单的正则匹配
        patterns = {
            "customer_name": r"客户[：:]\s*([^\n\r]+)",
            "project_name": r"项目[：:]\s*([^\n\r]+)",
            "amount": r"金额[：:]\s*([^\n\r]+)",
            "phone": r"电话[：:]\s*([^\n\r]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                result[key] = match.group(1).strip()
        
        return result
    
    def _can_access_project(self, user: User, project: Project) -> bool:
        """检查用户是否可以访问项目"""
        return (user.role == "admin" or 
                project.creator_id == user.id or 
                project.designer_id == user.id)
    
    def _can_modify_project(self, user: User, project: Project) -> bool:
        """检查用户是否可以修改项目"""
        return (user.role == "admin" or 
                project.creator_id == user.id or 
                project.designer_id == user.id)
    
    def _is_number(self, s: str) -> bool:
        """检查字符串是否为数字"""
        try:
            float(s)
            return True
        except ValueError:
            return False