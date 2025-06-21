#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - OCR服务实现
提供图片文字识别和信息提取功能
"""

import io
import base64
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import pytesseract
import cv2
import numpy as np

from app.ai.service import get_ai_service

class OCRService:
    """OCR服务类"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        
        # 配置Tesseract路径（Windows需要）
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    async def recognize_project_notebook(self, image_data: bytes) -> Dict[str, Any]:
        """识别项目笔记本图片"""
        try:
            # 1. 图片预处理
            processed_image = self._preprocess_image(image_data)
            
            # 2. OCR识别
            ocr_text = self._perform_ocr(processed_image)
            
            if not ocr_text or len(ocr_text.strip()) < 10:
                return {
                    "success": False,
                    "error": "无法识别图片中的文字"
                }
            
            # 3. AI提取信息
            extraction_result = await self.ai_service.extract_from_ocr(ocr_text)
            
            if extraction_result["success"]:
                return {
                    "success": True,
                    "ocr_text": ocr_text,
                    "extracted_info": extraction_result["extracted_info"],
                    "confidence": self._calculate_confidence(extraction_result["extracted_info"])
                }
            else:
                # 返回原始OCR文本，让用户手动输入
                return {
                    "success": True,
                    "ocr_text": ocr_text,
                    "extracted_info": {},
                    "confidence": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR处理失败: {str(e)}"
            }
    
    def _preprocess_image(self, image_data: bytes) -> np.ndarray:
        """图片预处理"""
        # 将字节数据转换为图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为OpenCV格式
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 转为灰度图
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # 去噪
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 二值化
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 膨胀操作，使文字更清晰
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.dilate(binary, kernel, iterations=1)
        
        return processed
    
    def _perform_ocr(self, image: np.ndarray) -> str:
        """执行OCR识别"""
        # 使用Tesseract进行OCR
        custom_config = r'--oem 3 --psm 6 -l chi_sim+eng'
        text = pytesseract.image_to_string(image, config=custom_config)
        
        # 清理识别结果
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        return cleaned_text
    
    def _calculate_confidence(self, extracted_info: Dict[str, Any]) -> float:
        """计算识别置信度"""
        required_fields = ["customer_name", "project_name"]
        optional_fields = ["amount", "phone", "email", "deadline"]
        
        score = 0
        
        # 必填字段
        for field in required_fields:
            if extracted_info.get(field):
                score += 30
        
        # 可选字段
        for field in optional_fields:
            if extracted_info.get(field):
                score += 10
        
        return min(score, 100) / 100

# 单例模式
_ocr_service = None

def get_ocr_service() -> OCRService:
    """获取OCR服务实例"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service