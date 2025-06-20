# 宝塔面板集成配置指南

## 一、快速部署步骤

### 1. 在宝塔面板创建站点
- 站点名称：`ai-manager-system`
- PHP版本：纯静态
- 数据库：MySQL 5.7+
- FTP：不创建

### 2. 安装必要软件
在宝塔软件商店安装：
- Python 项目管理器
- Supervisor 管理器
- Redis (可选)
- MySQL 5.7+

### 3. 克隆项目
```bash
cd /www/wwwroot
git clone https://github.com/your-username/ai-manager-system.git
cd ai-manager-system