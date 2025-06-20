#!/bin/bash
# AI管理系统 - 自动备份脚本
# 支持数据库备份、文件备份、远程备份

set -e

# ========== 配置区 ==========
# 项目配置
PROJECT_NAME="ai-manager-system"
PROJECT_DIR="/www/wwwroot/${PROJECT_NAME}"
BACKUP_BASE="/www/backup/${PROJECT_NAME}"
LOG_FILE="/www/wwwlogs/${PROJECT_NAME}/backup.log"

# 数据库配置（从.env文件读取）
if [ -f "${PROJECT_DIR}/.env" ]; then
    source ${PROJECT_DIR}/.env
fi

# 备份配置
BACKUP_KEEP_DAYS=30  # 本地备份保留天数
BACKUP_KEEP_WEEKLY=12  # 每周备份保留数量
BACKUP_KEEP_MONTHLY=6  # 每月备份保留数量

# 远程备份配置（可选）
REMOTE_BACKUP_ENABLE=false
REMOTE_BACKUP_HOST=""
REMOTE_BACKUP_USER=""
REMOTE_BACKUP_PATH=""
REMOTE_BACKUP_KEY=""

# ========== 函数定义 ==========

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

# 错误处理
error_exit() {
    log "错误: $1"
    exit 1
}

# 创建备份目录
create_backup_dirs() {
    mkdir -p ${BACKUP_BASE}/{daily,weekly,monthly,temp}
    mkdir -p $(dirname ${LOG_FILE})
}

# 备份MySQL数据库
backup_mysql() {
    log "开始备份MySQL数据库..."
    
    # 解析数据库连接信息
    if [[ $DATABASE_URL =~ mysql://([^:]+):([^@]+)@([^/]+)/(.+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASS="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_NAME="${BASH_REMATCH[4]}"
    else
        log "警告: 未找到MySQL配置，跳过数据库备份"
        return
    fi
    
    DUMP_FILE="${BACKUP_BASE}/temp/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"
    
    # 执行备份
    mysqldump -h${DB_HOST} -u${DB_USER} -p${DB_PASS} \
        --single-transaction \
        --routines \
        --triggers \
        --add-drop-database \
        --databases ${DB_NAME} > ${DUMP_FILE} 2>/dev/null
    
    if [ $? -eq 0 ]; then
        # 压缩备份文件
        gzip ${DUMP_FILE}
        log "数据库备份完成: ${DUMP_FILE}.gz"
        echo "${DUMP_FILE}.gz"
    else
        error_exit "数据库备份失败"
    fi
}

# 备份SQLite数据库
backup_sqlite() {
    log "开始备份SQLite数据库..."
    
    DB_FILE="${PROJECT_DIR}/data/ai_manager.db"
    if [ ! -f "${DB_FILE}" ]; then
        log "警告: SQLite数据库文件不存在"
        return
    fi
    
    BACKUP_FILE="${BACKUP_BASE}/temp/ai_manager_$(date +%Y%m%d_%H%M%S).db"
    
    # 使用SQLite备份命令
    sqlite3 ${DB_FILE} ".backup '${BACKUP_FILE}'"
    
    if [ $? -eq 0 ]; then
        gzip ${BACKUP_FILE}
        log "SQLite备份完成: ${BACKUP_FILE}.gz"
        echo "${BACKUP_FILE}.gz"
    else
        error_exit "SQLite备份失败"
    fi
}

# 备份上传文件
backup_uploads() {
    log "开始备份上传文件..."
    
    UPLOAD_DIR="${PROJECT_DIR}/data/uploads"
    if [ ! -d "${UPLOAD_DIR}" ]; then
        log "警告: 上传目录不存在"
        return
    fi
    
    BACKUP_FILE="${BACKUP_BASE}/temp/uploads_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # 创建压缩包
    tar -czf ${BACKUP_FILE} -C ${PROJECT_DIR}/data uploads/ 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log "上传文件备份完成: ${BACKUP_FILE}"
        echo "${BACKUP_FILE}"
    else
        error_exit "上传文件备份失败"
    fi
}

# 备份配置文件
backup_configs() {
    log "开始备份配置文件..."
    
    CONFIG_FILE="${BACKUP_BASE}/temp/configs_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # 备份重要配置文件
    tar -czf ${CONFIG_FILE} \
        -C ${PROJECT_DIR} \
        .env \
        docker-compose.yml \
        nginx.conf \
        deploy/ \
        2>/dev/null || true
    
    if [ -f ${CONFIG_FILE} ]; then
        log "配置文件备份完成: ${CONFIG_FILE}"
        echo "${CONFIG_FILE}"
    fi
}

# 整合备份文件
create_full_backup() {
    log "创建完整备份包..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    FULL_BACKUP="${BACKUP_BASE}/temp/full_backup_${TIMESTAMP}.tar"
    
    # 创建备份清单
    cat > ${BACKUP_BASE}/temp/manifest.txt << EOF
AI管理系统完整备份
备份时间: $(date)
备份版本: $(cd ${PROJECT_DIR} && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
备份内容:
- 数据库备份
- 上传文件
- 配置文件
EOF
    
    # 打包所有备份文件
    cd ${BACKUP_BASE}/temp
    tar -cf ${FULL_BACKUP} *.gz *.txt 2>/dev/null
    
    if [ $? -eq 0 ]; then
        gzip ${FULL_BACKUP}
        log "完整备份创建成功: ${FULL_BACKUP}.gz"
        echo "${FULL_BACKUP}.gz"
    else
        error_exit "创建完整备份失败"
    fi
}

# 分类存储备份
organize_backup() {
    local backup_file=$1
    local backup_name=$(basename ${backup_file})
    
    # 每日备份
    cp ${backup_file} ${BACKUP_BASE}/daily/
    
    # 每周备份（周日）
    if [ $(date +%w) -eq 0 ]; then
        cp ${backup_file} ${BACKUP_BASE}/weekly/
        log "创建每周备份: ${backup_name}"
    fi
    
    # 每月备份（每月1号）
    if [ $(date +%d) -eq 01 ]; then
        cp ${backup_file} ${BACKUP_BASE}/monthly/
        log "创建每月备份: ${backup_name}"
    fi
}

# 清理旧备份
cleanup_old_backups() {
    log "清理旧备份文件..."
    
    # 清理每日备份
    find ${BACKUP_BASE}/daily -name "*.gz" -mtime +${BACKUP_KEEP_DAYS} -delete
    
    # 清理每周备份（保留最近N个）
    ls -t ${BACKUP_BASE}/weekly/*.gz 2>/dev/null | tail -n +$((BACKUP_KEEP_WEEKLY + 1)) | xargs rm -f
    
    # 清理每月备份（保留最近N个）
    ls -t ${BACKUP_BASE}/monthly/*.gz 2>/dev/null | tail -n +$((BACKUP_KEEP_MONTHLY + 1)) | xargs rm -f
    
    # 清理临时文件
    rm -f ${BACKUP_BASE}/temp/*
    
    log "旧备份清理完成"
}

# 远程备份
remote_backup() {
    local backup_file=$1
    
    if [ "${REMOTE_BACKUP_ENABLE}" != "true" ]; then
        return
    fi
    
    log "开始远程备份..."
    
    # 使用rsync同步到远程服务器
    rsync -avz -e "ssh -i ${REMOTE_BACKUP_KEY}" \
        ${backup_file} \
        ${REMOTE_BACKUP_USER}@${REMOTE_BACKUP_HOST}:${REMOTE_BACKUP_PATH}/
    
    if [ $? -eq 0 ]; then
        log "远程备份成功"
    else
        log "警告: 远程备份失败"
    fi
}

# 发送备份报告
send_backup_report() {
    local status=$1
    local backup_file=$2
    
    # 这里可以集成邮件通知或企业微信通知
    # 为第6轮企业微信集成预留
    log "备份状态: ${status}"
}

# ========== 主流程 ==========

main() {
    log "========== 开始备份任务 =========="
    
    # 创建备份目录
    create_backup_dirs
    
    # 执行备份
    DB_BACKUP=""
    UPLOAD_BACKUP=""
    CONFIG_BACKUP=""
    
    # 备份数据库
    if [[ $DATABASE_URL == mysql://* ]]; then
        DB_BACKUP=$(backup_mysql)
    elif [[ $DATABASE_URL == sqlite://* ]]; then
        DB_BACKUP=$(backup_sqlite)
    fi
    
    # 备份文件
    UPLOAD_BACKUP=$(backup_uploads)
    CONFIG_BACKUP=$(backup_configs)
    
    # 创建完整备份
    FULL_BACKUP=$(create_full_backup)
    
    if [ -n "${FULL_BACKUP}" ]; then
        # 分类存储
        organize_backup ${FULL_BACKUP}
        
        # 远程备份
        remote_backup ${FULL_BACKUP}
        
        # 清理旧备份
        cleanup_old_backups
        
        # 发送报告
        send_backup_report "成功" ${FULL_BACKUP}
        
        log "========== 备份任务完成 =========="
        exit 0
    else
        send_backup_report "失败" ""
        error_exit "备份任务失败"
    fi
}

# 执行主流程
main