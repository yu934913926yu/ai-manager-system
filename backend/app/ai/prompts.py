"""
AI提示词模板管理
针对不同业务场景优化的提示词
"""

from typing import Dict, Any
from datetime import datetime

class PromptManager:
    """提示词管理器"""
    
    def __init__(self):
        self.system_prompts = {
            "default": self._get_default_system_prompt(),
            "project_analysis": self._get_project_analysis_system_prompt(),
            "information_extraction": self._get_extraction_system_prompt(),
            "status_update": self._get_status_update_system_prompt(),
            "reminder_generation": self._get_reminder_system_prompt()
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """获取系统提示词"""
        prompt_type = context.get("type", "default")
        return self.system_prompts.get(prompt_type, self.system_prompts["default"])
    
    def _get_default_system_prompt(self) -> str:
        """默认系统提示词"""
        return """你是一个专业的AI运营总管，负责协助广告公司管理项目流程。

你的职责包括：
1. 协助项目信息记录和管理
2. 提供项目状态分析和建议
3. 生成专业的项目报告和提醒
4. 帮助优化工作流程

请始终保持专业、准确、高效的回复风格。"""
    
    def _get_project_analysis_system_prompt(self) -> str:
        """项目分析系统提示词"""
        return """你是一个专业的项目分析师，专门分析广告设计项目。

分析时请关注：
1. 项目复杂度和可行性
2. 潜在风险和挑战
3. 建议的执行步骤
4. 时间和资源评估

请以JSON格式返回分析结果，包含以下字段：
- summary: 项目概述
- complexity_level: 复杂度(低/中/高)
- estimated_hours: 预估工时
- risks: 潜在风险列表
- suggestions: 执行建议列表
- priority: 优先级(低/正常/高/紧急)"""
    
    def _get_extraction_system_prompt(self) -> str:
        """信息提取系统提示词"""
        return """你是一个专业的信息提取专家，从文本中提取项目相关信息。

请从提供的文本中提取以下信息：
- customer_name: 客户名称
- project_name: 项目名称
- contact_person: 联系人
- phone: 电话号码
- email: 邮箱地址
- amount: 项目金额
- deadline: 截止时间
- requirements: 项目要求
- notes: 其他备注

请以JSON格式返回提取结果，如果某个字段无法确定，请设为null。"""
    
    def _get_status_update_system_prompt(self) -> str:
        """状态更新系统提示词"""
        return """你是一个专业的项目经理，负责生成项目状态更新说明。

请生成简洁、专业的状态更新描述，说明：
1. 项目当前进展
2. 状态变更的原因
3. 下一步行动计划

保持语言简洁、客观、专业。"""
    
    def _get_reminder_system_prompt(self) -> str:
        """提醒生成系统提示词"""
        return """你是一个专业的助理，负责生成项目提醒信息。

请生成清晰、actionable的提醒文本，包含：
1. 明确的行动要求
2. 相关的项目信息
3. 时间敏感性提示

语言要友善但有紧迫感，确保信息传达清楚。"""
    
    def get_project_analysis_prompt(self, project_data: Dict[str, Any]) -> str:
        """项目分析提示词"""
        return f"""请分析以下项目信息：

项目名称：{project_data.get('project_name', '未知')}
客户：{project_data.get('customer_name', '未知')}
项目类型：{project_data.get('category', '未知')}
报价金额：{project_data.get('quoted_price', '未报价')}
截止时间：{project_data.get('deadline', '未设定')}
项目描述：{project_data.get('description', '无描述')}

请提供专业的项目分析。"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """信息提取提示词"""
        return f"""请从以下文本中提取项目信息：

{text}

请返回JSON格式的结构化数据。"""
    
    def get_status_update_prompt(self, project_data: Dict, old_status: str, new_status: str) -> str:
        """状态更新提示词"""
        return f"""项目状态更新：

项目：{project_data.get('project_name', '未知项目')}
客户：{project_data.get('customer_name', '未知客户')}
状态变更：{old_status} → {new_status}
更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

请生成一段专业的状态更新说明。"""
    
    def get_reminder_prompt(self, reminder_type: str, data: Dict[str, Any]) -> str:
        """提醒生成提示词"""
        templates = {
            "deadline_warning": f"""项目即将到期提醒：

项目：{data.get('project_name', '未知项目')}
客户：{data.get('customer_name', '未知客户')}
截止时间：{data.get('deadline', '未知')}
当前状态：{data.get('status', '未知')}

请生成一个专业的截止时间提醒。""",
            
            "payment_reminder": f"""收款提醒：

项目：{data.get('project_name', '未知项目')}
客户：{data.get('customer_name', '未知客户')}
应收金额：{data.get('amount', '未知')}
账期：{data.get('due_date', '未知')}

请生成一个礼貌但明确的收款提醒。""",
            
            "status_stuck": f"""项目进度提醒：

项目：{data.get('project_name', '未知项目')}
当前状态：{data.get('status', '未知')}
停留时间：{data.get('stuck_days', 0)}天

请生成一个项目进度跟进提醒。"""
        }
        
        return templates.get(reminder_type, f"请为{reminder_type}生成提醒文本：{data}")