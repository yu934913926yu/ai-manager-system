# AI管理系统 Dockerfile - 多阶段构建
# 支持开发和生产环境

# 阶段1: Python基础镜像
FROM python:3.10-slim as python-base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.5.1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 阶段2: 依赖安装
FROM python-base as dependencies

WORKDIR /app

# 复制依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# 阶段3: 开发环境
FROM dependencies as development

# 安装开发依赖
RUN pip install \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy \
    ipython

# 复制应用代码
COPY backend/ /app/

# 设置工作目录权限
RUN chown -R appuser:appuser /app

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8000

# 开发环境启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 阶段4: 生产环境构建
FROM dependencies as builder

WORKDIR /app

# 复制应用代码
COPY backend/ /app/

# 编译Python文件为字节码
RUN python -m compileall -b .

# 删除源文件，只保留字节码
RUN find . -name "*.py" -type f -delete

# 阶段5: 生产环境
FROM python-base as production

# 安装生产环境系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmysqlclient21 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从依赖阶段复制Python包
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# 从构建阶段复制编译后的应用
COPY --from=builder /app /app

# 创建必要的目录
RUN mkdir -p /app/data/uploads /app/data/backups /app/logs && \
    chown -R appuser:appuser /app

# 设置文件权限
RUN chmod -R 755 /app && \
    chmod -R 777 /app/data /app/logs

# 健康检查脚本
COPY --chown=appuser:appuser deploy/docker/healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh || exit 1

# 生产环境启动命令
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]