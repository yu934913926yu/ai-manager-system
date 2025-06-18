#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 001 初始数据表迁移
创建所有核心业务表和基础数据
"""

from datetime import datetime
from sqlalchemy import text
from app.database import engine, Base
from app.models import (
    User, Project, Supplier, Task, ProjectFile, 
    ProjectStatusLog, FinancialRecord, AIConversation, SystemConfig
)
from app import RoleEnum, StatusEnum

# 迁移信息
MIGRATION_VERSION = "001"
MIGRATION_NAME = "init_tables"
MIGRATION_DESCRIPTION = "创建AI管理系统初始数据表结构"

def upgrade():
    """执行数据库升级"""
    print(f"🔄 执行迁移 {MIGRATION_VERSION}: {MIGRATION_NAME}")
    
    try:
        # 1. 创建所有表
        print("📊 创建数据表...")
        Base.metadata.create_all(bind=engine)
        
        # 2. 插入初始数据
        print("📝 插入初始数据...")
        insert_initial_data()
        
        # 3. 创建索引 (如果需要额外的索引)
        print("🔍 创建索引...")
        create_indexes()
        
        # 4. 插入迁移记录
        print("📋 记录迁移历史...")
        record_migration()
        
        print(f"✅ 迁移 {MIGRATION_VERSION} 完成")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        # 这里可以添加回滚逻辑
        raise

def downgrade():
    """执行数据库降级 (删除所有表)"""
    print(f"⚠️  执行迁移回滚 {MIGRATION_VERSION}: {MIGRATION_NAME}")
    
    try:
        # 删除所有表 (谨慎操作!)
        Base.metadata.drop_all(bind=engine)
        print(f"🗑️  迁移 {MIGRATION_VERSION} 已回滚")
        
    except Exception as e:
        print(f"❌ 回滚失败: {e}")
        raise

def insert_initial_data():
    """插入初始数据"""
    from sqlalchemy.orm import Session
    
    with Session(engine) as session:
        try:
            # 1. 创建默认管理员用户
            admin_user = session.query(User).filter(User.username == "admin").first()
            if not admin_user:
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                
                admin_user = User(
                    username="admin",
                    email="admin@aimanager.com",
                    password_hash=pwd_context.hash("admin123456"),  # 默认密码
                    full_name="系统管理员",
                    role=RoleEnum.ADMIN,
                    is_active=True,
                    is_admin=True,
                    created_at=datetime.utcnow()
                )
                session.add(admin_user)
                print("👤 创建默认管理员用户: admin/admin123456")
            
            # 2. 创建示例设计师用户
            designer_user = session.query(User).filter(User.username == "designer").first()
            if not designer_user:
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                
                designer_user = User(
                    username="designer",
                    email="designer@aimanager.com",
                    password_hash=pwd_context.hash("designer123"),
                    full_name="示例设计师",
                    role=RoleEnum.DESIGNER,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(designer_user)
                print("🎨 创建示例设计师用户: designer/designer123")
            
            # 3. 创建示例财务用户
            finance_user = session.query(User).filter(User.username == "finance").first()
            if not finance_user:
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                
                finance_user = User(
                    username="finance",
                    email="finance@aimanager.com", 
                    password_hash=pwd_context.hash("finance123"),
                    full_name="示例财务",
                    role=RoleEnum.FINANCE,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(finance_user)
                print("💰 创建示例财务用户: finance/finance123")
            
            # 4. 插入系统配置
            configs = [
                {
                    "config_key": "system_name",
                    "config_value": "AI管理系统",
                    "config_type": "string",
                    "description": "系统名称",
                    "category": "basic"
                },
                {
                    "config_key": "company_name", 
                    "config_value": "您的公司名称",
                    "config_type": "string",
                    "description": "公司名称",
                    "category": "basic"
                },
                {
                    "config_key": "project_number_prefix",
                    "config_value": "PRJ",
                    "config_type": "string", 
                    "description": "项目编号前缀",
                    "category": "project"
                },
                {
                    "config_key": "auto_project_number",
                    "config_value": "true",
                    "config_type": "boolean",
                    "description": "是否自动生成项目编号",
                    "category": "project"
                },
                {
                    "config_key": "default_currency",
                    "config_value": "CNY",
                    "config_type": "string",
                    "description": "默认货币",
                    "category": "financial"
                },
                {
                    "config_key": "ai_auto_response",
                    "config_value": "true",
                    "config_type": "boolean",
                    "description": "AI是否自动回复",
                    "category": "ai"
                }
            ]
            
            for config_data in configs:
                existing_config = session.query(SystemConfig).filter(
                    SystemConfig.config_key == config_data["config_key"]
                ).first()
                
                if not existing_config:
                    config = SystemConfig(**config_data)
                    session.add(config)
            
            print("⚙️  插入系统默认配置")
            
            # 5. 插入示例供应商
            suppliers_data = [
                {
                    "name": "优质印刷厂",
                    "service_type": "印刷服务",
                    "contact_person": "张经理",
                    "phone": "138-0000-0001",
                    "rating": 8,
                    "business_scope": "各类印刷品制作"
                },
                {
                    "name": "创意设计工作室",
                    "service_type": "设计外包",
                    "contact_person": "李设计师",
                    "phone": "139-0000-0002", 
                    "rating": 9,
                    "business_scope": "品牌设计、包装设计"
                },
                {
                    "name": "专业摄影团队",
                    "service_type": "摄影服务",
                    "contact_person": "王摄影师",
                    "phone": "137-0000-0003",
                    "rating": 7,
                    "business_scope": "产品摄影、商业摄影"
                }
            ]
            
            for supplier_data in suppliers_data:
                existing_supplier = session.query(Supplier).filter(
                    Supplier.name == supplier_data["name"]
                ).first()
                
                if not existing_supplier:
                    supplier = Supplier(**supplier_data)
                    session.add(supplier)
            
            print("🏢 插入示例供应商数据")
            
            # 提交事务
            session.commit()
            print("✅ 初始数据插入完成")
            
        except Exception as e:
            session.rollback()
            print(f"❌ 初始数据插入失败: {e}")
            raise

def create_indexes():
    """创建额外的数据库索引"""
    with engine.connect() as connection:
        try:
            # 项目表的复合索引
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_projects_customer_status 
                ON projects(customer_name, status);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_projects_creator_date 
                ON projects(creator_id, created_at);
            """))
            
            # 任务表索引
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project_status 
                ON tasks(project_id, status);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tasks_assignee_due 
                ON tasks(assignee_id, due_date);
            """))
            
            # AI对话表索引
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_date 
                ON ai_conversations(wechat_userid, created_at);
            """))
            
            # 文件表索引
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_project_files_type_date 
                ON project_files(file_type, uploaded_at);
            """))
            
            connection.commit()
            print("📇 数据库索引创建完成")
            
        except Exception as e:
            connection.rollback()
            print(f"⚠️  索引创建警告: {e}")

def record_migration():
    """记录迁移历史"""
    with engine.connect() as connection:
        try:
            # 创建迁移历史表 (如果不存在)
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY,
                    version VARCHAR(10) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    executed_at DATETIME NOT NULL,
                    execution_time FLOAT
                );
            """))
            
            # 插入本次迁移记录
            connection.execute(text("""
                INSERT OR IGNORE INTO migration_history 
                (version, name, description, executed_at, execution_time)
                VALUES (:version, :name, :description, :executed_at, :execution_time);
            """), {
                "version": MIGRATION_VERSION,
                "name": MIGRATION_NAME,
                "description": MIGRATION_DESCRIPTION,
                "executed_at": datetime.utcnow(),
                "execution_time": 0.0  # 这里可以记录实际执行时间
            })
            
            connection.commit()
            print("📝 迁移历史记录完成")
            
        except Exception as e:
            connection.rollback()
            print(f"⚠️  迁移记录警告: {e}")

def check_migration_status():
    """检查迁移状态"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT COUNT(*) as table_count FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%';
            """))
            
            table_count = result.fetchone()[0]
            
            if table_count > 0:
                print(f"📊 数据库包含 {table_count} 个表")
                
                # 检查核心表是否存在
                core_tables = ['users', 'projects', 'suppliers', 'tasks']
                for table in core_tables:
                    result = connection.execute(text(f"""
                        SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='table' AND name='{table}';
                    """))
                    exists = result.fetchone()[0] > 0
                    status = "✅" if exists else "❌"
                    print(f"  {status} {table}")
                
                return True
            else:
                print("📊 数据库为空，需要执行迁移")
                return False
                
    except Exception as e:
        print(f"⚠️  无法检查迁移状态: {e}")
        return False

def get_migration_info():
    """获取迁移信息"""
    return {
        "version": MIGRATION_VERSION,
        "name": MIGRATION_NAME,
        "description": MIGRATION_DESCRIPTION,
        "upgrade_function": upgrade,
        "downgrade_function": downgrade,
        "check_function": check_migration_status
    }

if __name__ == "__main__":
    """直接运行迁移脚本"""
    print("🔧 AI管理系统数据库迁移工具")
    print("=" * 50)
    
    # 检查当前状态
    if check_migration_status():
        print("数据库已初始化")
    else:
        print("开始执行数据库迁移...")
        upgrade()
    
    print("=" * 50)