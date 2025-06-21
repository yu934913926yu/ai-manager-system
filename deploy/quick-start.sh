#!/bin/bash
# AI管理系统快速启动脚本

set -e

echo "🚀 AI管理系统快速部署"
echo "======================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python版本: $python_version"

# 创建虚拟环境
echo "📦 创建Python虚拟环境..."
cd backend
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "📥 安装后端依赖..."
pip install -r requirements.txt

# 复制环境配置
if [ ! -f .env ]; then
    echo "⚙️ 创建环境配置文件..."
    cp .env.example .env
    echo "请编辑 backend/.env 文件配置必要的参数"
fi

# 初始化数据库
echo "🗄️ 初始化数据库..."
python migrate.py init

# 安装前端依赖
echo "📥 安装前端依赖..."
cd ../frontend
npm install

# 构建前端
echo "🔨 构建前端应用..."
npm run build

echo ""
echo "✅ 部署准备完成！"
echo ""
echo "启动步骤："
echo "1. 编辑 backend/.env 配置文件"
echo "2. 启动后端: cd backend && python main.py"
echo "3. 启动前端: cd frontend && npm run dev"
echo ""
echo "访问地址:"
echo "- 前端: http://localhost:5173"
echo "- API文档: http://localhost:8000/docs"