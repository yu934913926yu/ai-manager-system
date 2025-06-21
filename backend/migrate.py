#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 数据库迁移工具
支持数据库初始化、迁移和种子数据导入
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.database import Base, engine, get_db
from app.models import User, Project, Task, Supplier
from app.auth import get_password_hash
from app.config import get_settings
from app import RoleEnum, StatusEnum

settings = get_settings()

class DatabaseMigration:
    """数据库迁移管理器"""
    
    def __init__(self):
        self.engine = engine
        
    def create_database(self):
        """创建数据库（仅MySQL）"""
        if settings.DATABASE_URL.startswith("mysql"):
            try:
                # 提取数据库名
                db_name = settings.DATABASE_URL.split('/')[-1].split('?')[0]
                
                # 创建临时引擎连接到MySQL服务器
                temp_url = settings.DATABASE_URL.rsplit('/', 1)[0]
                temp_engine = create_engine(temp_url)
                
                with temp_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    conn.commit()
                    
                print(f"✅ 数据库 {db_name} 创建成功")
                
            except Exception as e:
                print(f"❌ 创建数据库失败: {e}")
                sys.exit(1)
    
    def create_tables(self):
        """创建所有数据表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("✅ 数据表创建成功")
        except Exception as e:
            print(f"❌ 创建数据表失败: {e}")
            sys.exit(1)
    
    def drop_tables(self):
        """删除所有数据表"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            print("✅ 数据表删除成功")
        except Exception as e:
            print(f"❌ 删除数据表失败: {e}")
            sys.exit(1)
    
    def create_default_users(self):
        """创建默认用户"""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as db:
            try:
                # 检查是否已有用户
                existing_users = db.query(User).count()
                if existing_users > 0:
                    print("⚠️  已存在用户，跳过创建默认用户")
                    return
                
                # 创建管理员
                admin = User(
                    username="admin",
                    email="admin@ai-manager.com",
                    full_name="系统管理员",
                    password_hash=get_password_hash("admin123"),
                    role=RoleEnum.ADMIN,
                    is_admin=True,
                    is_active=True
                )
                db.add(admin)
                
                # 创建设计师
                designer = User(
                    username="designer",
                    email="designer@ai-manager.com",
                    full_name="张设计师",
                    password_hash=get_password_hash("design123"),
                    role=RoleEnum.DESIGNER,
                    is_active=True
                )
                db.add(designer)
                
                # 创建财务
                finance = User(
                    username="finance",
                    email="finance@ai-manager.com",
                    full_name="李财务",
                    password_hash=get_password_hash("finance123"),
                    role=RoleEnum.FINANCE,
                    is_active=True
                )
                db.add(finance)
                
                db.commit()
                print("✅ 默认用户创建成功")
                print("   管理员: admin / admin123")
                print("   设计师: designer / design123")
                print("   财务: finance / finance123")
                
            except Exception as e:
                db.rollback()
                print(f"❌ 创建默认用户失败: {e}")
    
    def create_sample_data(self):
        """创建示例数据"""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as db:
            try:
                # 获取用户
                admin = db.query(User).filter(User.username == "admin").first()
                designer = db.query(User).filter(User.username == "designer").first()
                
                if not admin or not designer:
                    print("⚠️  找不到默认用户，跳过创建示例数据")
                    return
                
                # 创建示例项目
                projects = [
                    Project(
                        project_number=f"PRJ{datetime.now().strftime('%Y%m%d')}001",
                        project_name="2025春节营销物料设计",
                        customer_name="张三商贸有限公司",
                        customer_phone="138-0000-0001",
                        project_type="设计",
                        status=StatusEnum.IN_DESIGN,
                        priority="high",
                        quoted_price=8000,
                        creator_id=admin.id,
                        designer_id=designer.id,
                        requirements="设计春节主题海报、易拉宝、展板等物料"
                    ),
                    Project(
                        project_number=f"PRJ{datetime.now().strftime('%Y%m%d')}002",
                        project_name="品牌VI设计",
                        customer_name="李四科技公司",
                        customer_phone="139-0000-0002",
                        project_type="设计",
                        status=StatusEnum.PENDING_QUOTE,
                        priority="normal",
                        creator_id=admin.id,
                        requirements="全套VI设计，包括LOGO、名片、信纸等"
                    )
                ]
                
                for project in projects:
                    db.add(project)
                
                # 创建示例供应商
                suppliers = [
                    Supplier(
                        name="优质印刷厂",
                        company_name="优质印刷有限公司",
                        service_type="印刷",
                        contact_person="王经理",
                        phone="130-0000-0001",
                        rating=8,
                        is_preferred=True
                    ),
                    Supplier(
                        name="快捷制作",
                        company_name="快捷广告制作中心",
                        service_type="制作",
                        contact_person="赵经理",
                        phone="131-0000-0002",
                        rating=7
                    )
                ]
                
                for supplier in suppliers:
                    db.add(supplier)
                
                db.commit()
                print("✅ 示例数据创建成功")
                
            except Exception as e:
                db.rollback()
                print(f"❌ 创建示例数据失败: {e}")
    
    def migrate(self):
        """执行完整迁移"""
        print("🚀 开始数据库迁移...")
        
        # 1. 创建数据库
        self.create_database()
        
        # 2. 创建表
        self.create_tables()
        
        # 3. 创建默认用户
        self.create_default_users()
        
        # 4. 创建示例数据（可选）
        if "--with-sample" in sys.argv:
            self.create_sample_data()
        
        print("✅ 数据库迁移完成！")
    
    def reset(self):
        """重置数据库"""
        print("⚠️  警告：此操作将删除所有数据！")
        confirm = input("确认重置数据库？(yes/no): ")
        
        if confirm.lower() == "yes":
            print("🔄 重置数据库...")
            self.drop_tables()
            self.migrate()
        else:
            print("❌ 操作已取消")

def main():
    """主函数"""
    migration = DatabaseMigration()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python migrate.py migrate [--with-sample]  # 执行迁移")
        print("  python migrate.py reset                    # 重置数据库")
        print("  python migrate.py create-tables            # 仅创建表")
        print("  python migrate.py create-users             # 仅创建用户")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "migrate":
        migration.migrate()
    elif command == "reset":
        migration.reset()
    elif command == "create-tables":
        migration.create_tables()
    elif command == "create-users":
        migration.create_default_users()
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()