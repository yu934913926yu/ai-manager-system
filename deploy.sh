#!/bin/bash
# AI管理系统 - 宝塔部署脚本
# 自动化部署流程，支持初始部署和更新

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 部署配置
PROJECT_NAME="ai-manager-system"
PROJECT_DIR="/www/wwwroot/${PROJECT_NAME}"
BACKUP_DIR="/www/backup/${PROJECT_NAME}"
LOG_FILE="/www/wwwlogs/${PROJECT_NAME}-deploy.log"

# 函数：打印彩色消息
print_message() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a ${LOG_FILE}
}

# 函数：检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_message "错误: $1 命令未找到，请先安装" "$RED"
        exit 1
    fi
}

# 函数：创建必要的目录
create_directories() {
    print_message "创建必要的目录..." "$BLUE"
    
    mkdir -p ${PROJECT_DIR}/{data,logs,deploy}
    mkdir -p ${PROJECT_DIR}/data/{uploads,backups}
    mkdir -p ${PROJECT_DIR}/deploy/{nginx,mysql,docker}
    mkdir -p ${BACKUP_DIR}
    
    # 设置权限
    chmod -R 755 ${PROJECT_DIR}
    chmod -R 777 ${PROJECT_DIR}/data
    chmod -R 777 ${PROJECT_DIR}/logs
    
    print_message "目录创建完成" "$GREEN"
}

# 函数：备份现有数据
backup_data() {
    if [ -d "${PROJECT_DIR}/data" ]; then
        print_message "备份现有数据..." "$BLUE"
        
        BACKUP_NAME="backup-$(date '+%Y%m%d-%H%M%S')"
        tar -czf ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz \
            -C ${PROJECT_DIR} \
            data/ \
            .env \
            docker-compose.yml \
            2>/dev/null || true
        
        print_message "数据备份完成: ${BACKUP_NAME}.tar.gz" "$GREEN"
    fi
}

# 函数：拉取最新代码
pull_code() {
    print_message "拉取最新代码..." "$BLUE"
    
    cd ${PROJECT_DIR}
    
    if [ -d ".git" ]; then
        git pull origin main
    else
        print_message "未找到Git仓库，请先手动克隆项目" "$RED"
        exit 1
    fi
    
    print_message "代码更新完成" "$GREEN"
}

# 函数：构建前端
build_frontend() {
    print_message "构建前端应用..." "$BLUE"
    
    cd ${PROJECT_DIR}/frontend
    
    # 安装依赖
    npm install --registry=https://registry.npmmirror.com
    
    # 构建生产版本
    npm run build
    
    print_message "前端构建完成" "$GREEN"
}

# 函数：配置环境变量
setup_env() {
    print_message "配置环境变量..." "$BLUE"
    
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        cp ${PROJECT_DIR}/.env.example ${PROJECT_DIR}/.env
        
        print_message "请编辑 .env 文件配置必要的环境变量" "$YELLOW"
        print_message "配置完成后重新运行部署脚本" "$YELLOW"
        exit 0
    fi
    
    # 加载环境变量
    source ${PROJECT_DIR}/.env
    
    print_message "环境变量配置完成" "$GREEN"
}

# 函数：初始化数据库
init_database() {
    print_message "初始化数据库..." "$BLUE"
    
    # 创建MySQL初始化脚本
    cat > ${PROJECT_DIR}/deploy/mysql/init.sql << EOF
-- AI管理系统数据库初始化脚本
CREATE DATABASE IF NOT EXISTS ai_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_manager;

-- 创建初始用户
GRANT ALL PRIVILEGES ON ai_manager.* TO 'ai_user'@'%' IDENTIFIED BY 'ai_pass_2024';
FLUSH PRIVILEGES;
EOF
    
    print_message "数据库初始化脚本创建完成" "$GREEN"
}

# 函数：配置宝塔站点
setup_bt_site() {
    print_message "配置宝塔站点..." "$BLUE"
    
    # 创建宝塔Nginx配置
    cat > ${PROJECT_DIR}/deploy/nginx/bt_site.conf << 'EOF'
# 宝塔面板站点配置
# 请在宝塔面板中创建站点后，将此配置复制到站点配置中

location / {
    root /www/wwwroot/ai-manager-system/frontend/dist;
    try_files $uri $uri/ /index.html;
}

location /api {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /uploads {
    alias /www/wwwroot/ai-manager-system/data/uploads;
    expires 30d;
}

location /ws {
    proxy_pass http://127.0.0.1:8000/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
EOF
    
    print_message "宝塔站点配置创建完成" "$GREEN"
    print_message "请在宝塔面板中配置站点并导入配置" "$YELLOW"
}

# 函数：启动Docker服务
start_docker() {
    print_message "启动Docker服务..." "$BLUE"
    
    cd ${PROJECT_DIR}
    
    # 停止旧容器
    docker-compose down || true
    
    # 构建并启动新容器
    docker-compose up -d --build
    
    # 等待服务启动
    print_message "等待服务启动..." "$YELLOW"
    sleep 10
    
    # 检查服务状态
    docker-compose ps
    
    print_message "Docker服务启动完成" "$GREEN"
}

# 函数：健康检查
health_check() {
    print_message "执行健康检查..." "$BLUE"
    
    # 检查后端API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_message "后端API: 正常" "$GREEN"
    else
        print_message "后端API: 异常" "$RED"
    fi
    
    # 检查前端
    if curl -f http://localhost/index.html > /dev/null 2>&1; then
        print_message "前端应用: 正常" "$GREEN"
    else
        print_message "前端应用: 异常" "$RED"
    fi
    
    # 检查数据库
    if docker exec ai_manager_mysql mysqladmin ping -h localhost > /dev/null 2>&1; then
        print_message "MySQL数据库: 正常" "$GREEN"
    else
        print_message "MySQL数据库: 异常" "$RED"
    fi
}

# 函数：清理旧备份
cleanup_backups() {
    print_message "清理旧备份..." "$BLUE"
    
    # 保留最近7天的备份
    find ${BACKUP_DIR} -name "backup-*.tar.gz" -mtime +7 -delete
    
    print_message "旧备份清理完成" "$GREEN"
}

# 主函数
main() {
    print_message "==============================" "$BLUE"
    print_message "AI管理系统部署脚本" "$BLUE"
    print_message "==============================" "$BLUE"
    
    # 检查必要的命令
    check_command docker
    check_command docker-compose
    check_command git
    check_command npm
    check_command curl
    
    # 执行部署步骤
    create_directories
    backup_data
    pull_code
    setup_env
    build_frontend
    init_database
    setup_bt_site
    start_docker
    health_check
    cleanup_backups
    
    print_message "==============================" "$GREEN"
    print_message "部署完成！" "$GREEN"
    print_message "==============================" "$GREEN"
    
    print_message "请完成以下步骤:" "$YELLOW"
    print_message "1. 在宝塔面板中创建站点" "$YELLOW"
    print_message "2. 配置SSL证书" "$YELLOW"
    print_message "3. 导入Nginx配置" "$YELLOW"
    print_message "4. 配置防火墙规则" "$YELLOW"
    print_message "5. 设置定时备份任务" "$YELLOW"
}

# 运行主函数
main "$@"