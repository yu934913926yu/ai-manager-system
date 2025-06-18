# 🚀 AI管理系统 (AI Manager System)

## 📋 项目简介
一个基于AI的企业级项目管理系统，集成企业微信机器人与Web管理后台，实现项目管理的智能化、自动化。

## 🏗️ 系统架构
- **后端**: Python + FastAPI + SQLite/MySQL
- **前端**: Vue.js 3 + Element Plus
- **AI服务**: Claude/Gemini + OCR识别
- **消息入口**: 企业微信机器人
- **部署**: Docker + 宝塔面板

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- MySQL 8.0+ (生产环境)

### 本地开发
```bash
# 1. 克隆项目
git clone https://github.com/your-username/ai-manager-system.git
cd ai-manager-system

# 2. 后端setup
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# 3. 前端setup
cd ../frontend
npm install
npm run dev

# 4. 启动后端
cd ../backend
python main.py

宝塔部署
详见 docs/DEPLOY.md
📚 文档

API文档
部署指南
开发指南

📞 联系方式

开发者: [Your Name]
邮箱: [your-email@example.com]

📄 许可证
MIT License