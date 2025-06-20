#!/bin/bash
# AI管理系统 - 启动脚本
# 用于系统启动时自动运行必要的服务

set -e

# 配置
PROJECT_NAME="ai-manager-system"
PROJECT_DIR="/www/wwwroot/${PROJECT_NAME}"
LOG_FILE="/www/wwwlogs/${PROJECT_NAME}/startup.log"
VENV_PATH="${PROJECT_DIR}/venv"
BACKEND_DIR="${PROJECT_DIR}/backend"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a ${LOG_FILE}
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓ $1${NC}" | tee -a ${LOG_FILE}
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗ $1${NC}" | tee -a ${LOG_FILE}
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}" | tee -a ${LOG_FILE}
}

# 检查系统依赖
check_dependencies() {
    log "检查系统依赖..."
    
    # 检查Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        log_success "Python ${PYTHON_VERSION} 已安装"
    else
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查MySQL
    if command -v mysql &> /dev/null; then
        log_success "MySQL 客户端已安装"
    else
        log_warning "MySQL 客户端未安装"
    fi
    
    # 检查Redis
    if command -v redis-cli &> /dev/null; then
        log_success "Redis 客户端已安装"
    else
        log_warning "Redis 客户端未安装"
    fi
    
    # 检查Supervisor
    if command -v supervisorctl &> /dev/null; then
        log_success "Supervisor 已安装"
    else
        log_error "Supervisor 未安装"
        exit 1
    fi
}

# 检查目录权限
check_permissions() {
    log "检查目录权限..."
    
    # 确保目录存在
    mkdir -p ${PROJECT_DIR}/{data/uploads,data/backups,logs}
    mkdir -p /www/wwwlogs/${PROJECT_NAME}
    
    # 设置权限
    chown -R www:www ${PROJECT_DIR}/data
    chown -R www:www ${PROJECT_DIR}/logs
    chown -R www:www /www/wwwlogs/${PROJECT_NAME}
    
    chmod -R 755 ${PROJECT_DIR}
    chmod -R 777 ${PROJECT_DIR}/data
    chmod -R 777 ${PROJECT_DIR}/logs
    
    log_success "目录权限设置完成"
}

# 激活虚拟环境
activate_venv() {
    log "激活Python虚拟环境..."
    
    if [ ! -d "${VENV_PATH}" ]; then
        log_warning "虚拟环境不存在，正在创建..."
        python3 -m venv ${VENV_PATH}
    fi
    
    source ${VENV_PATH}/bin/activate
    log_success "虚拟环境已激活"
}

# 安装/更新依赖
install_dependencies() {
    log "检查Python依赖..."
    
    cd ${BACKEND_DIR}
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    # 安装生产环境额外依赖
    pip install gunicorn
    
    log_success "Python依赖安装完成"
}

# 数据库迁移
migrate_database() {
    log "执行数据库迁移..."
    
    cd ${BACKEND_DIR}
    
    # 检查数据库连接
    python -c "from app.database import test_connection; exit(0 if test_connection() else 1)"
    
    if [ $? -eq 0 ]; then
        # 执行迁移
        python migrate.py migrate
        log_success "数据库迁移完成"
    else
        log_error "数据库连接失败"
        exit 1
    fi
}

# 收集静态文件
collect_static() {
    log "收集静态文件..."
    
    # 确保前端构建文件存在
    if [ -d "${PROJECT_DIR}/frontend/dist" ]; then
        log_success "前端静态文件就绪"
    else
        log_warning "前端静态文件不存在，请运行 npm run build"
    fi
}

# 启动服务
start_services() {
    log "启动应用服务..."
    
    # 重新加载Supervisor配置
    supervisorctl reread
    supervisorctl update
    
    # 启动主服务
    supervisorctl start ai_manager_backend
    
    # 检查服务状态
    sleep 5
    if supervisorctl status ai_manager_backend | grep -q RUNNING; then
        log_success "后端服务启动成功"
    else
        log_error "后端服务启动失败"
        supervisorctl tail -f ai_manager_backend stderr
        exit 1
    fi
    
    # 如果Celery配置存在，启动异步任务服务
    if [ -f "${BACKEND_DIR}/app/tasks/celery_app.py" ]; then
        supervisorctl start ai_manager_celery || true
        supervisorctl start ai_manager_beat || true
        log_success "异步任务服务已启动"
    fi
}

# 健康检查
health_check() {
    log "执行健康检查..."
    
    # 等待服务完全启动
    sleep 10
    
    # 检查API健康状态
    HEALTH_URL="http://127.0.0.1:8000/health"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${HEALTH_URL})
    
    if [ "${HTTP_CODE}" = "200" ]; then
        log_success "API健康检查通过"
        
        # 获取详细状态
        curl -s ${HEALTH_URL} | python -m json.tool
    else
        log_error "API健康检查失败 (HTTP ${HTTP_CODE})"
        
        # 显示错误日志
        tail -n 50 /www/wwwlogs/${PROJECT_NAME}/error.log
        exit 1
    fi
}

# 设置定时任务
setup_cron() {
    log "设置定时任务..."
    
    # 备份任务 - 每天凌晨2点执行
    CRON_BACKUP="0 2 * * * /bin/bash ${PROJECT_DIR}/deploy/scripts/backup.sh >> /www/wwwlogs/${PROJECT_NAME}/backup-cron.log 2>&1"
    
    # 日志清理 - 每天凌晨3点执行
    CRON_CLEANUP="0 3 * * * find ${PROJECT_DIR}/logs -name '*.log' -mtime +30 -delete"
    
    # 添加到crontab
    (crontab -l 2>/dev/null | grep -v "${PROJECT_NAME}"; echo "# ${PROJECT_NAME} 定时任务"; echo "${CRON_BACKUP}"; echo "${CRON_CLEANUP}") | crontab -
    
    log_success "定时任务设置完成"
}

# 显示启动信息
show_info() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}   AI管理系统启动完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${BLUE}访问地址:${NC} http://your-domain.com"
    echo -e "${BLUE}API文档:${NC} http://your-domain.com/docs"
    echo -e "${BLUE}健康检查:${NC} http://your-domain.com/health"
    echo -e "${GREEN}========================================${NC}\n"
}

# 主函数
main() {
    log "========== AI管理系统启动 =========="
    
    # 创建日志目录
    mkdir -p $(dirname ${LOG_FILE})
    
    # 执行启动步骤
    check_dependencies
    check_permissions
    activate_venv
    install_dependencies
    migrate_database
    collect_static
    start_services
    health_check
    setup_cron
    
    # 显示完成信息
    show_info
    
    log "========== 启动流程完成 =========="
}

# 执行主函数
main