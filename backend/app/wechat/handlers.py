#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 企业微信消息处理器（完整版）
处理各种类型的消息和指令，集成AI服务
"""

import re
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, date

from sqlalchemy.orm import Session
from app.database import get_db_context
from app.models import User, Project, Task, Supplier
from app.wechat.utils import WeChatUtils
from app.ai.service import get_ai_service
from app.ai.ocr import get_ocr_service
from app import StatusEnum

class MessageHandler:
    """消息处理器"""
    
    def __init__(self):
        self.utils = WeChatUtils()
        self.ai_service = get_ai_service()
        self.ocr_service = get_ocr_service()
        
        # 指令映射
        self.commands = {
            "帮助": self.handle_help,
            "help": self.handle_help,
            "创建": self.handle_create_project,
            "新建": self.handle_create_project,
            "查询": self.handle_query_project,
            "查看": self.handle_query_project,
            "更新": self.handle_update_status,
            "状态": self.handle_status_update,
            "我的": self.handle_my_projects,
            "项目": self.handle_my_projects,
            "统计": self.handle_statistics,
            "供应商": self.handle_supplier_query,
            "确认": self.handle_confirm_creation,
            "取消": self.handle_cancel_operation,
            "分析": self.handle_project_analysis
        }
        
        # 临时存储用户的项目创建信息
        self.pending_projects = {}
    
    async def handle_text_message(self, content: str, wechat_userid: str, user: Optional[User]) -> str:
        """处理文本消息"""
        content = content.strip()
        
        # 检查用户是否绑定
        if not user:
            return self._handle_unbound_user(content, wechat_userid)
        
        # 处理@机器人的消息
        if content.startswith("@AI总管") or content.startswith("@AI运营总管"):
            content = re.sub(r"@AI[运营]*总管\s*", "", content).strip()
        
        # 空消息处理
        if not content:
            return "您好！我是AI运营总管，输入'帮助'查看可用指令。"
        
        # 命令匹配和处理
        for keyword, handler in self.commands.items():
            if content.startswith(keyword):
                params = content[len(keyword):].strip()
                try:
                    return await handler(params, user)
                except Exception as e:
                    print(f"❌ 处理指令 '{keyword}' 失败: {e}")
                    return f"处理指令时出错，请稍后重试。错误：{str(e)}"
        
        # 智能识别项目信息 (OCR后的文本或结构化输入)
        if await self._is_project_info(content):
            return await self.handle_text_project_creation(content, user)
        
        # 默认智能问答
        return await self.handle_smart_qa(content, user)
    
    async def handle_image_message(self, data: Dict[str, Any], wechat_userid: str, user: Optional[User]) -> str:
        """处理图片消息 - 集成OCR"""
        if not user:
            return "请先完成账户绑定后再上传图片。"
        
        try:
            media_id = data.get('MediaId', '')
            print(f"📷 处理图片消息: MediaId={media_id}")
            
            # 下载图片
            image_data = self.utils.download_media(media_id)
            if not image_data:
                return "图片下载失败，请重试。如问题持续，请联系管理员。"
            
            # OCR识别
            print("🔍 开始OCR识别...")
            ocr_result = await self.ocr_service.recognize_project_notebook(image_data)
            
            if ocr_result["success"]:
                extracted_info = ocr_result.get("extracted_info", {})
                ocr_text = ocr_result.get("ocr_text", "")
                confidence = ocr_result.get("confidence", 0)
                
                print(f"✅ OCR识别成功，置信度: {confidence}")
                
                if extracted_info.get("customer_name") and extracted_info.get("project_name"):
                    # 保存到临时存储
                    self.pending_projects[wechat_userid] = {
                        "extracted_info": extracted_info,
                        "ocr_text": ocr_text,
                        "timestamp": datetime.now()
                    }
                    
                    return f"""📷 图片识别完成：

👤 客户：{extracted_info.get('customer_name')}
📝 项目：{extracted_info.get('project_name')}
💰 金额：{extracted_info.get('amount', '未识别')}
📞 电话：{extracted_info.get('phone', '未识别')}
✉️ 邮箱：{extracted_info.get('email', '未识别')}
📅 截止：{extracted_info.get('deadline', '未识别')}
📋 要求：{extracted_info.get('requirements', '未识别')}

请确认信息是否正确：
- 回复 '确认' 创建项目
- 回复 '取消' 重新操作
- 回复 '修改 字段名 新值' 修改信息"""
                else:
                    return f"""📷 图片识别完成，但项目信息不完整：

识别到的文字：
{ocr_text}

提取的信息：
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}

请补充缺失信息或重新拍照。也可以手动输入项目信息。"""
            else:
                error_msg = ocr_result.get("error", "未知错误")
                return f"""📷 图片识别失败：{error_msg}

建议：
1. 确保图片清晰，文字可读
2. 重新拍照尝试
3. 手动输入项目信息

输入 '创建' 开始手动创建项目"""
                
        except Exception as e:
            print(f"❌ 图片处理异常: {e}")
            return f"图片处理时出现异常，请重试。如问题持续，请联系技术支持。\n\n错误详情：{str(e)}"
    
    async def handle_file_message(self, data: Dict[str, Any], wechat_userid: str, user: Optional[User]) -> str:
        """处理文件消息"""
        if not user:
            return "请先完成账户绑定后再上传文件。"
        
        try:
            filename = data.get('Title', '未知文件')
            file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
            
            # 根据文件类型提供不同处理
            if file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif']:
                return "检测到图片文件，请直接发送图片而不是文件，以便进行OCR识别。"
            elif file_ext in ['pdf', 'doc', 'docx']:
                return f"📄 已收到文档：{filename}\n\n文档已保存，如需提取项目信息，请发送文档的截图。"
            elif file_ext in ['xls', 'xlsx']:
                return f"📊 已收到表格：{filename}\n\n表格已保存，可通过Web管理界面查看详情。"
            else:
                return f"📎 已收到文件：{filename}\n\n文件已保存，可通过Web管理界面查看和下载。"
                
        except Exception as e:
            return f"文件处理失败：{str(e)}"
    
    async def handle_help(self, params: str, user: User) -> str:
        """处理帮助指令"""
        if params:
            # 具体指令帮助
            help_details = {
                "创建": """📋 创建项目指令：

方式1：拍照创建
- 直接拍摄项目笔记本
- AI自动识别项目信息
- 确认后自动创建

方式2：手动创建
- 创建 [客户名] [项目名] [金额]
- 例：创建 张三公司 LOGO设计 5000

方式3：结构化创建
- 客户：XX公司
- 项目：XX设计
- 金额：XXXX元""",
                
                "查询": """🔍 查询项目指令：

- 查询 [项目编号]
- 查看 [项目编号]
- 我的项目 (查看我负责的项目)

例：查询 PRJ20240101001""",
                
                "更新": """🔄 更新项目指令：

- 更新 [项目编号] [新状态]
- 状态 [项目编号] [新状态]

可用状态：
待报价、已报价、客户确认、定金已付、
设计中、待客户确认、客户定稿、生产中、
项目完成、尾款已付""",
                
                "供应商": """🏢 供应商查询：

- 供应商 (查看所有类型)
- 供应商 [服务类型]

例：供应商 印刷"""
            }
            
            return help_details.get(params, f"未找到 '{params}' 的详细帮助")
        
        # 通用帮助
        help_text = f"""🤖 AI运营总管指令帮助

👋 欢迎，{user.full_name or user.username}！

📋 **项目管理**
• 创建 [项目信息] - 创建新项目
• 查询 [项目编号] - 查询项目详情
• 更新 [项目编号] [状态] - 更新项目状态
• 我的项目 - 查看我负责的项目

📊 **数据统计**
• 统计 - 查看项目统计信息
• 供应商 [类型] - 查询供应商信息

🤖 **AI功能**
• 分析 [项目编号] - AI项目分析
• 直接拍照笔记本 - 自动识别项目信息
• 直接提问 - 智能问答

💡 **使用技巧**
• 支持语音转文字输入
• 可以用自然语言描述问题
• 输入 '帮助 [指令名]' 查看详细说明

❓ 遇到问题请联系管理员
📖 更多功能请访问Web管理界面"""

        return help_text
    
    async def handle_create_project(self, params: str, user: User) -> str:
        """处理创建项目指令"""
        if not params:
            return """📋 创建项目说明：

方式1：简单创建
创建 [客户名] [项目名] [金额]
例：创建 张三公司 LOGO设计 5000

方式2：结构化输入
客户：张三公司
项目：LOGO设计
金额：5000元
电话：138-0000-0001

方式3：拍照创建
直接拍摄项目笔记本，AI自动识别"""
        
        try:
            # 解析参数
            parts = params.split()
            if len(parts) < 2:
                return "项目信息不完整，请提供至少客户名称和项目名称。\n\n格式：创建 [客户名] [项目名] [金额]"
            
            customer_name = parts[0]
            
            # 解析金额和项目名称
            quoted_price = None
            if len(parts) > 2 and self._is_number(parts[-1].replace('元', '').replace(',', '')):
                quoted_price = float(parts[-1].replace('元', '').replace(',', ''))
                project_name = " ".join(parts[1:-1])
            else:
                project_name = " ".join(parts[1:])
            
            # 创建项目
            result = await self._create_project_in_db(
                customer_name=customer_name,
                project_name=project_name,
                quoted_price=quoted_price,
                creator=user
            )
            
            if result["success"]:
                project = result["project"]
                
                # 生成AI项目分析
                try:
                    analysis = await self.ai_service.analyze_project({
                        "project_name": project_name,
                        "customer_name": customer_name,
                        "quoted_price": quoted_price
                    })
                    
                    analysis_text = f"\n\n🤖 AI分析：{analysis.get('summary', '暂无分析')}"
                    if analysis.get('suggestions'):
                        analysis_text += f"\n💡 建议：{'; '.join(analysis['suggestions'][:2])}"
                except Exception:
                    analysis_text = ""
                
                return f"""✅ 项目创建成功！

🆔 项目编号：{project.project_number}
👤 客户：{customer_name}
📝 项目：{project_name}
💰 报价：{quoted_price or '待报价'}
📊 状态：{StatusEnum.PENDING_QUOTE}
👨‍💼 创建人：{user.full_name or user.username}{analysis_text}"""
            else:
                return f"❌ 项目创建失败：{result['error']}"
                
        except Exception as e:
            return f"❌ 项目创建失败：{str(e)}"
    
    async def handle_query_project(self, params: str, user: User) -> str:
        """处理查询项目指令"""
        if not params:
            return "请提供项目编号。\n\n格式：查询 PRJ20240101001"
        
        project_number = params.strip().upper()
        
        with get_db_context() as db:
            project = db.query(Project).filter(
                Project.project_number == project_number
            ).first()
            
            if not project:
                return f"❌ 未找到项目编号：{project_number}\n\n💡 提示：\n- 检查编号是否正确\n- 输入 '我的项目' 查看相关项目"
            
            # 权限检查
            if not self._can_access_project(user, project):
                return "❌ 您没有权限查看此项目"
            
            # 获取相关人员信息
            creator_name = "未知"
            designer_name = "未分配"
            
            if project.creator_id:
                creator = db.query(User).filter(User.id == project.creator_id).first()
                creator_name = creator.full_name or creator.username if creator else "未知"
            
            if project.designer_id:
                designer = db.query(User).filter(User.id == project.designer_id).first()
                designer_name = designer.full_name or designer.username if designer else "未分配"
            
            # 构建项目信息
            info = f"""📋 项目详情

🆔 项目编号：{project.project_number}
👤 客户：{project.customer_name}
📝 项目：{project.project_name}
📊 状态：{project.status}
💰 报价：{project.quoted_price or '未报价'}
👨‍💼 创建人：{creator_name}
🎨 设计师：{designer_name}
📅 创建时间：{project.created_at.strftime('%Y-%m-%d %H:%M')}"""
            
            if project.customer_phone:
                info += f"\n📞 客户电话：{project.customer_phone}"
            
            if project.deadline:
                info += f"\n⏰ 截止时间：{project.deadline}"
            
            if project.description:
                info += f"\n📋 项目描述：{project.description}"
            
            if project.notes:
                info += f"\n📝 备注：{project.notes}"
            
            # 获取任务信息
            tasks = db.query(Task).filter(Task.project_id == project.id).all()
            if tasks:
                info += f"\n\n📋 相关任务 ({len(tasks)}个)："
                for task in tasks[:3]:  # 只显示前3个
                    info += f"\n• {task.title} ({task.status})"
                if len(tasks) > 3:
                    info += f"\n• ... 还有{len(tasks)-3}个任务"
            
            return info
    
    async def handle_update_status(self, params: str, user: User) -> str:
        """处理状态更新指令"""
        parts = params.split(maxsplit=1)
        if len(parts) < 2:
            return """📊 状态更新格式：

更新 [项目编号] [新状态]

可用状态：
• 待报价 • 已报价 • 客户确认
• 定金已付 • 设计中 • 待客户确认
• 客户定稿 • 生产中 • 项目完成
• 尾款已付

例：更新 PRJ20240101001 设计中"""
        
        project_number, new_status = parts
        project_number = project_number.strip().upper()
        new_status = new_status.strip()
        
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
            "尾款已付": StatusEnum.PAID,
            "已归档": StatusEnum.ARCHIVED
        }
        
        if new_status not in status_mapping:
            available_statuses = "、".join(status_mapping.keys())
            return f"❌ 无效状态：{new_status}\n\n可用状态：{available_statuses}"
        
        with get_db_context() as db:
            project = db.query(Project).filter(
                Project.project_number == project_number
            ).first()
            
            if not project:
                return f"❌ 未找到项目编号：{project_number}"
            
            if not self._can_modify_project(user, project):
                return "❌ 您没有权限修改此项目状态"
            
            old_status = project.status
            mapped_status = status_mapping[new_status]
            
            # 更新状态
            project.status = mapped_status
            project.updated_at = datetime.utcnow()
            
            # 根据状态更新时间戳
            if mapped_status == StatusEnum.IN_DESIGN and not project.started_at:
                project.started_at = datetime.utcnow()
            elif mapped_status == StatusEnum.COMPLETED and not project.completed_at:
                project.completed_at = datetime.utcnow()
            
            try:
                # 生成AI状态更新说明
                update_description = await self.ai_service.generate_status_update(
                    {
                        "project_name": project.project_name,
                        "customer_name": project.customer_name,
                        "project_number": project.project_number
                    },
                    old_status,
                    new_status
                )
            except Exception:
                update_description = "状态更新完成"
            
            return f"""✅ 项目状态更新成功！

🆔 {project_number}
📊 {old_status} → {new_status}
👨‍💼 操作人：{user.full_name or user.username}
🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

🤖 {update_description}"""
    
    async def handle_my_projects(self, params: str, user: User) -> str:
        """处理我的项目指令"""
        status_filter = params.strip() if params else None
        
        with get_db_context() as db:
            query = db.query(Project).filter(
                (Project.creator_id == user.id) | (Project.designer_id == user.id)
            )
            
            if status_filter and status_filter in ["进行中", "已完成", "待报价"]:
                if status_filter == "进行中":
                    query = query.filter(Project.status.in_([
                        StatusEnum.IN_DESIGN, StatusEnum.IN_PRODUCTION
                    ]))
                elif status_filter == "已完成":
                    query = query.filter(Project.status == StatusEnum.COMPLETED)
                elif status_filter == "待报价":
                    query = query.filter(Project.status == StatusEnum.PENDING_QUOTE)
            
            projects = query.order_by(Project.updated_at.desc()).limit(10).all()
            
            if not projects:
                filter_text = f"({status_filter})" if status_filter else ""
                return f"📋 您暂时没有相关项目{filter_text}"
            
            result = f"📋 我的项目列表 ({len(projects)}个)：\n\n"
            
            for i, project in enumerate(projects, 1):
                role = "创建" if project.creator_id == user.id else "设计"
                result += f"📌 {i}. {project.project_number}\n"
                result += f"   👤 {project.customer_name} - {project.project_name}\n"
                result += f"   📊 {project.status} | 👤 {role}者\n"
                if project.quoted_price:
                    result += f"   💰 {project.quoted_price}元\n"
                result += "   ────────────\n"
            
            if len(projects) == 10:
                result += "\n💡 只显示最近10个项目，更多请访问Web界面"
            
            return result
    
    async def handle_statistics(self, params: str, user: User) -> str:
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
            
            pending_quote = db.query(Project).filter(
                Project.status == StatusEnum.PENDING_QUOTE
            ).count()
            
            # 个人统计
            my_completed = db.query(Project).filter(
                (Project.creator_id == user.id) | (Project.designer_id == user.id),
                Project.status == StatusEnum.COMPLETED
            ).count()
            
            my_in_progress = db.query(Project).filter(
                (Project.creator_id == user.id) | (Project.designer_id == user.id),
                Project.status.in_([StatusEnum.IN_DESIGN, StatusEnum.IN_PRODUCTION])
            ).count()
            
            return f"""📊 项目统计信息

🏢 **公司整体**
• 总项目数：{total_projects}
• 进行中：{in_progress}
• 已完成：{completed}
• 待报价：{pending_quote}

👤 **我的项目**
• 相关项目：{my_projects}
• 进行中：{my_in_progress}
• 已完成：{my_completed}
• 完成率：{round(my_completed/my_projects*100, 1) if my_projects > 0 else 0}%

📅 统计时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

💡 详细数据请访问Web管理界面"""
    
    async def handle_supplier_query(self, params: str, user: User) -> str:
        """处理供应商查询指令"""
        with get_db_context() as db:
            if params:
                # 按类型查询
                suppliers = db.query(Supplier).filter(
                    Supplier.service_type.like(f"%{params}%")
                ).order_by(Supplier.rating.desc()).limit(5).all()
                
                if not suppliers:
                    return f"❌ 未找到'{params}'类型的供应商\n\n💡 输入 '供应商' 查看所有类型"
                
                result = f"🏢 {params}类供应商推荐：\n\n"
                for i, supplier in enumerate(suppliers, 1):
                    result += f"📌 {i}. {supplier.name}\n"
                    result += f"   📞 {supplier.phone or '未提供'}\n"
                    result += f"   ⭐ 评分：{supplier.rating}/10\n"
                    if supplier.is_preferred:
                        result += "   🌟 优选供应商\n"
                    result += "   ────────────\n"
                
                return result
            else:
                # 显示供应商类型
                service_types = db.query(Supplier.service_type).distinct().all()
                types_list = [t[0] for t in service_types if t[0]]
                
                if not types_list:
                    return "🏢 暂无供应商信息"
                
                return f"🏢 可查询的供应商类型：\n\n" + "\n".join([f"• {t}" for t in types_list]) + \
                       f"\n\n💡 用法：供应商 [类型名]\n例：供应商 印刷"
    
    async def handle_confirm_creation(self, params: str, user: User) -> str:
        """处理确认创建指令"""
        wechat_userid = user.wechat_userid
        if not wechat_userid or wechat_userid not in self.pending_projects:
            return "❌ 没有待确认的项目信息\n\n💡 请先拍照或输入项目信息"
        
        try:
            pending = self.pending_projects[wechat_userid]
            extracted_info = pending["extracted_info"]
            
            # 创建项目
            result = await self._create_project_in_db(
                customer_name=extracted_info.get("customer_name"),
                project_name=extracted_info.get("project_name"),
                quoted_price=self._parse_amount(extracted_info.get("amount")),
                customer_phone=extracted_info.get("phone"),
                customer_email=extracted_info.get("email"),
                description=extracted_info.get("requirements"),
                deadline=self._parse_date(extracted_info.get("deadline")),
                creator=user
            )
            
            if result["success"]:
                project = result["project"]
                
                # 清除临时数据
                del self.pending_projects[wechat_userid]
                
                return f"""✅ 项目创建成功！

🆔 项目编号：{project.project_number}
👤 客户：{project.customer_name}
📝 项目：{project.project_name}
💰 报价：{project.quoted_price or '待报价'}
📊 状态：{project.status}

🎉 项目已成功录入系统！"""
            else:
                return f"❌ 项目创建失败：{result['error']}"
                
        except Exception as e:
            return f"❌ 确认创建失败：{str(e)}"
    
    async def handle_cancel_operation(self, params: str, user: User) -> str:
        """处理取消操作指令"""
        wechat_userid = user.wechat_userid
        if wechat_userid and wechat_userid in self.pending_projects:
            del self.pending_projects[wechat_userid]
            return "✅ 已取消当前操作\n\n💡 可以重新拍照或手动输入项目信息"
        else:
            return "ℹ️ 没有进行中的操作需要取消"
    
    async def handle_project_analysis(self, params: str, user: User) -> str:
        """处理项目分析指令"""
        if not params:
            return "请提供项目编号。\n\n格式：分析 PRJ20240101001"
        
        project_number = params.strip().upper()
        
        with get_db_context() as db:
            project = db.query(Project).filter(
                Project.project_number == project_number
            ).first()
            
            if not project:
                return f"❌ 未找到项目编号：{project_number}"
            
            if not self._can_access_project(user, project):
                return "❌ 您没有权限查看此项目"
            
            try:
                # 准备项目数据
                project_data = {
                    "project_name": project.project_name,
                    "customer_name": project.customer_name,
                    "category": project.category,
                    "quoted_price": float(project.quoted_price) if project.quoted_price else None,
                    "deadline": project.deadline.isoformat() if project.deadline else None,
                    "description": project.description,
                    "status": project.status
                }
                
                # AI分析
                analysis = await self.ai_service.analyze_project(project_data)
                
                result = f"""🤖 AI项目分析报告

🆔 项目：{project.project_number}
📝 {project.project_name}

📊 **分析结果**
{analysis.get('summary', '暂无分析')}

📈 **复杂度评估**
{analysis.get('complexity_level', '未知')}

⏱️ **预估工时**
{analysis.get('estimated_hours', '未估算')}小时

⚠️ **潜在风险**"""
                
                risks = analysis.get('risks', [])
                if risks:
                    for risk in risks[:3]:
                        result += f"\n• {risk}"
                else:
                    result += "\n• 暂无识别的风险"
                
                result += "\n\n💡 **执行建议**"
                suggestions = analysis.get('suggestions', [])
                if suggestions:
                    for suggestion in suggestions[:3]:
                        result += f"\n• {suggestion}"
                else:
                    result += "\n• 暂无建议"
                
                result += f"\n\n🎯 **优先级**: {analysis.get('priority', '正常')}"
                
                return result
                
            except Exception as e:
                return f"❌ AI分析失败：{str(e)}\n\n💡 请稍后重试或联系技术支持"
    
    async def handle_text_project_creation(self, content: str, user: User) -> str:
        """处理文本形式的项目创建"""
        try:
            # 使用AI提取项目信息
            extracted_info = await self.ai_service.extract_project_info(content)
            
            if extracted_info.get("error"):
                return f"❌ 无法解析项目信息：{extracted_info['error']}\n\n💡 请使用标准格式或拍照上传"
            
            if extracted_info.get("customer_name") and extracted_info.get("project_name"):
                # 保存到临时存储
                wechat_userid = user.wechat_userid
                self.pending_projects[wechat_userid] = {
                    "extracted_info": extracted_info,
                    "ocr_text": content,
                    "timestamp": datetime.now()
                }
                
                return f"""📝 文本识别完成：

👤 客户：{extracted_info.get('customer_name')}
📝 项目：{extracted_info.get('project_name')}
💰 金额：{extracted_info.get('amount', '未识别')}
📞 电话：{extracted_info.get('phone', '未识别')}
✉️ 邮箱：{extracted_info.get('email', '未识别')}

请确认信息是否正确：
- 回复 '确认' 创建项目
- 回复 '取消' 重新输入"""
            else:
                return "❌ 文本中缺少关键信息（客户名称或项目名称）\n\n💡 请补充完整信息后重试"
                
        except Exception as e:
            return f"❌ 文本解析失败：{str(e)}"
    
    async def handle_smart_qa(self, content: str, user: User) -> str:
        """智能问答处理 - 集成AI"""
        try:
            # 构建上下文
            context = {
                "type": "smart_qa",
                "user_role": user.role,
                "user_name": user.full_name or user.username,
                "system_info": "广告公司项目管理系统"
            }
            
            # 调用AI服务
            response = await self.ai_service.chat_completion(content, context)
            
            # 添加操作提示
            ai_response = response["content"]
            if "项目" in content and any(word in content for word in ["如何", "怎么", "怎样"]):
                ai_response += "\n\n💡 提示：您可以拍照笔记本或输入'创建'指令来创建项目"
            
            return ai_response
            
        except Exception as e:
            print(f"❌ AI服务调用失败: {e}")
            
            # 降级处理 - 简单的关键词匹配
            if "项目" in content and "多少" in content:
                with get_db_context() as db:
                    count = db.query(Project).filter(
                        (Project.creator_id == user.id) | (Project.designer_id == user.id)
                    ).count()
                    return f"您目前有 {count} 个相关项目。"
            
            if any(word in content for word in ["怎么", "如何", "怎样"]):
                return """您可以：
1. 拍照笔记本让我识别项目信息
2. 输入'创建'指令手动创建项目
3. 输入'帮助'查看更多指令
4. 直接提问，我会尽力回答"""
            
            return f"AI服务暂时不可用：{str(e)}\n\n💡 请尝试使用具体指令，如'帮助'查看可用功能。"
    
    # 辅助方法
    def _handle_unbound_user(self, content: str, wechat_userid: str) -> str:
        """处理未绑定用户"""
        return f"""👋 欢迎使用AI运营总管！

您的企业微信账号 ({wechat_userid}) 尚未绑定系统账户。

🔗 **如何绑定：**
请联系管理员将您的企业微信账号绑定到系统账户。

✨ **绑定后您可以：**
• 拍照自动创建项目
• 查询和更新项目状态  
• 接收智能提醒通知
• 使用AI分析功能
• 获取统计数据报告

如需帮助，请联系系统管理员。"""
    
    async def _is_project_info(self, content: str) -> bool:
        """判断是否为项目信息"""
        keywords = ["客户", "项目", "金额", "电话", "公司", "设计", "合同", "报价"]
        # 如果包含2个以上关键词，可能是项目信息
        return sum(1 for kw in keywords if kw in content) >= 2
    
    async def _create_project_in_db(
        self, 
        customer_name: str, 
        project_name: str, 
        creator: User,
        quoted_price: float = None,
        customer_phone: str = None,
        customer_email: str = None,
        description: str = None,
        deadline: date = None
    ) -> Dict[str, Any]:
        """在数据库中创建项目"""
        try:
            with get_db_context() as db:
                # 生成项目编号
                project_count = db.query(Project).count()
                project_number = f"PRJ{datetime.now().strftime('%Y%m%d')}{project_count + 1:03d}"
                
                # 创建项目
                project = Project(
                    project_number=project_number,
                    project_name=project_name,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    customer_email=customer_email,
                    description=description,
                    deadline=deadline,
                    quoted_price=quoted_price,
                    creator_id=creator.id,
                    status=StatusEnum.PENDING_QUOTE,
                    created_at=datetime.utcnow()
                )
                
                db.add(project)
                # db.commit() 会在 get_db_context 中自动调用
                
                return {"success": True, "project": project}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _can_access_project(self, user: User, project: Project) -> bool:
        """检查用户是否可以访问项目"""
        return (user.role == "admin" or 
                user.is_admin or
                project.creator_id == user.id or 
                project.designer_id == user.id)
    
    def _can_modify_project(self, user: User, project: Project) -> bool:
        """检查用户是否可以修改项目"""
        return (user.role == "admin" or 
                user.is_admin or
                project.creator_id == user.id or 
                project.designer_id == user.id)
    
    def _is_number(self, s: str) -> bool:
        """检查字符串是否为数字"""
        try:
            float(s)
            return True
        except ValueError:
            return False
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """解析金额字符串"""
        if not amount_str:
            return None
        
        try:
            # 清理字符串
            cleaned = re.sub(r'[^\d.]', '', str(amount_str))
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            # 尝试多种日期格式
            formats = ['%Y-%m-%d', '%Y/%m/%d', '%m-%d', '%m/%d']
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    # 如果只有月日，补充当前年份
                    if fmt in ['%m-%d', '%m/%d']:
                        parsed_date = parsed_date.replace(year=datetime.now().year)
                    return parsed_date
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None