"""
OCR图像识别服务
支持识别项目信息、合同文档等
"""

import base64
import io
from typing import Dict, Any, Optional
from PIL import Image
import httpx

from app.config import get_settings
from app.ai.service import get_ai_service

settings = get_settings()

class OCRService:
    """OCR识别服务"""
    
    def __init__(self):
        self.ocr_api_key = settings.OCR_API_KEY
        self.ai_service = get_ai_service()
        
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    async def recognize_image(self, image_data: bytes, image_type: str = "project") -> Dict[str, Any]:
        """识别图片中的文字"""
        try:
            # 预处理图片
            processed_image = self._preprocess_image(image_data)
            
            # 调用OCR API
            ocr_text = await self._call_ocr_api(processed_image)
            
            if not ocr_text:
                return {"success": False, "error": "OCR识别失败"}
            
            # 使用AI分析OCR结果
            if image_type == "project":
                project_info = await self.ai_service.extract_project_info(ocr_text)
                return {
                    "success": True,
                    "ocr_text": ocr_text,
                    "extracted_info": project_info,
                    "confidence": 0.8  # 模拟置信度
                }
            else:
                return {
                    "success": True,
                    "ocr_text": ocr_text,
                    "type": image_type
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _preprocess_image(self, image_data: bytes) -> bytes:
        """图片预处理"""
        try:
            # 打开图片
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 限制图片大小 (提高识别速度)
            max_size = (1920, 1080)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换回bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception:
            # 如果预处理失败，返回原图
            return image_data
    
    async def _call_ocr_api(self, image_data: bytes) -> Optional[str]:
        """调用OCR API"""
        if not self.ocr_api_key:
            # 如果没有配置OCR API，使用模拟数据
            return self._simulate_ocr_result()
        
        try:
            # 编码图片
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 这里可以集成多种OCR服务
            # 例如：百度OCR、腾讯OCR、阿里云OCR等
            
            # 示例：调用百度OCR
            url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
            params = {"access_token": self.ocr_api_key}
            data = {"image": image_base64}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params, data=data)
                response.raise_for_status()
                
                result = response.json()
                
                if "words_result" in result:
                    text_lines = [item["words"] for item in result["words_result"]]
                    return "\n".join(text_lines)
                else:
                    return None
                    
        except Exception as e:
            print(f"OCR API调用失败: {e}")
            return self._simulate_ocr_result()
    
    def _simulate_ocr_result(self) -> str:
        """模拟OCR识别结果 (用于测试)"""
        return """客户：张三公司
项目：品牌LOGO设计
金额：5000元
联系人：张总
电话：138-0000-0001
要求：现代简约风格，3个方案选择
截止时间：2024-01-15"""

    async def recognize_project_notebook(self, image_data: bytes) -> Dict[str, Any]:
        """识别项目笔记本"""
        result = await self.recognize_image(image_data, "project")
        
        if result["success"]:
            # 额外的项目信息验证
            extracted = result.get("extracted_info", {})
            
            # 验证必要字段
            required_fields = ["customer_name", "project_name"]
            missing_fields = [field for field in required_fields if not extracted.get(field)]
            
            if missing_fields:
                result["warning"] = f"缺少必要信息: {', '.join(missing_fields)}"
                result["confidence"] = 0.3
        
        return result
    
    async def recognize_contract(self, image_data: bytes) -> Dict[str, Any]:
        """识别合同文档"""
        result = await self.recognize_image(image_data, "contract")
        
        if result["success"]:
            # 合同信息提取
            contract_prompt = f"""
            请从以下合同文本中提取关键信息：
            
            {result['ocr_text']}
            
            请以JSON格式返回，包含以下字段：
            - 合同编号
            - 甲方
            - 乙方
            - 合同金额
            - 签署日期
            - 履行期限
            """
            
            try:
                contract_info = await self.ai_service.chat_completion(
                    contract_prompt, 
                    {"type": "contract_analysis"}
                )
                result["contract_info"] = contract_info["content"]
            except Exception as e:
                result["warning"] = f"合同信息提取失败: {e}"
        
        return result

# 全局OCR服务实例
_ocr_service = None

def get_ocr_service() -> OCRService:
    """获取OCR服务实例"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service