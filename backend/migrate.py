#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - 数据库迁移工具
用于管理数据库结构的创建、更新和维护
"""

import sys
import os
from pathlib import Path
import importlib.util
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import engine, test_connection
from app.config import get_settings

settings = get_settings()

class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self):
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations = []
        self.load_migrations()
    
    def load_migrations(self):
        """加载所有迁移脚本"""
        if not self.migrations_dir.exists():
            print("❌ 迁移目录不存在")
            return
        
        # 查找所有迁移文件
        migration_files = sorted([
            f for f in self.migrations_dir.glob("*.py") 
            if f.name != "__init__.py" and f.name.startswith(tuple("0123456789"))
        ])
        
        for migration_file in migration_files:
            try:
                # 动态导入迁移模块
                spec = importlib.util.spec_from_file_location(
                    migration_file.stem, migration_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 获取迁移信息
                if hasattr(module, 'get_migration_info'):
                    info = module.get_migration_info()
                    self.migrations.append({
                        "file": migration_file,
                        "module": module,
                        **info
                    })
                    
            except Exception as e:
                print(f"⚠️  加载迁移文件失败 {migration_file}: {e}")
        
        print(f"📂 加载了 {len(self.migrations)} 个迁移文件")
    
    def check_database(self):
        """检查数据库连接"""
        print("🔍 检查数据库连接...")
        
        if not test_connection():
            print("❌ 数据库连接失败")
            return False
        
        print(f"✅ 数据库连接成功: {settings.DATABASE_URL}")
        return True
    
    def show_status(self):
        """显示迁移状态"""
        print("\n📊 数据库迁移状态")
        print("-" * 60)
        
        if not self.migrations:
            print("没有找到迁移文件")
            return
        
        for migration in self.migrations:
            version = migration.get("version", "unknown")
            name = migration.get("name", "unnamed")
            description = migration.get("description", "无描述")
            
            # 检查是否已执行
            status = self.check_migration_executed(version)
            status_icon = "✅" if status else "⏳"
            
            print(f"{status_icon} {version}: {name}")
            print(f"   {description}")
        
        print("-" * 60)
    
    def check_migration_executed(self, version):
        """检查迁移是否已执行"""
        try:
            from sqlalchemy import text
            with engine.connect() as connection:
                # 检查迁移历史表是否存在
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name='migration_history';
                """))
                
                if result.fetchone()[0] == 0:
                    return False
                
                # 检查特定迁移是否已执行
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM migration_history 
                    WHERE version = :version;
                """), {"version": version})
                
                return result.fetchone()[0] > 0
                
        except Exception as e:
            print(f"⚠️  检查迁移状态失败: {e}")
            return False
    
    def run_migrations(self, target_version=None):
        """运行迁移"""
        print("\n🚀 开始执行数据库迁移")
        print("-" * 60)
        
        if not self.migrations:
            print("没有找到需要执行的迁移")
            return
        
        for migration in self.migrations:
            version = migration.get("version")
            name = migration.get("name")
            
            # 如果指定了目标版本，只执行到目标版本
            if target_version and version > target_version:
                break
            
            # 检查是否已执行
            if self.check_migration_executed(version):
                print(f"⏭️  跳过已执行的迁移 {version}: {name}")
                continue
            
            print(f"🔄 执行迁移 {version}: {name}")
            
            try:
                # 执行迁移
                upgrade_func = migration.get("upgrade_function")
                if upgrade_func:
                    start_time = datetime.now()
                    upgrade_func()
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    print(f"✅ 迁移 {version} 完成 (耗时: {duration:.2f}秒)")
                else:
                    print(f"⚠️  迁移 {version} 没有升级函数")
                    
            except Exception as e:
                print(f"❌ 迁移 {version} 执行失败: {e}")
                print("迁移已停止")
                return False
        
        print("-" * 60)
        print("✅ 所有迁移执行完成")
        return True
    
    def rollback_migration(self, version):
        """回滚特定迁移"""
        print(f"\n⚠️  回滚迁移 {version}")
        print("-" * 60)
        
        # 查找指定版本的迁移
        target_migration = None
        for migration in self.migrations:
            if migration.get("version") == version:
                target_migration = migration
                break
        
        if not target_migration:
            print(f"❌ 找不到版本 {version} 的迁移")
            return False
        
        try:
            downgrade_func = target_migration.get("downgrade_function")
            if downgrade_func:
                # 确认操作
                confirm = input(f"确定要回滚迁移 {version} 吗? 这可能会删除数据! (yes/no): ")
                if confirm.lower() != 'yes':
                    print("操作已取消")
                    return False
                
                downgrade_func()
                print(f"✅ 迁移 {version} 回滚完成")
                return True
            else:
                print(f"⚠️  迁移 {version} 没有回滚函数")
                return False
                
        except Exception as e:
            print(f"❌ 迁移回滚失败: {e}")
            return False
    
    def init_database(self):
        """初始化数据库"""
        print("\n🔧 初始化数据库")
        print("-" * 60)
        
        if not self.check_database():
            return False
        
        # 运行所有迁移
        return self.run_migrations()
    
    def reset_database(self):
        """重置数据库 (危险操作)"""
        print("\n⚠️  重置数据库")
        print("-" * 60)
        
        # 多重确认
        confirm1 = input("这将删除所有数据! 确定要继续吗? (yes/no): ")
        if confirm1.lower() != 'yes':
            print("操作已取消")
            return False
        
        confirm2 = input("请再次确认删除所有数据 (输入 'DELETE ALL'): ")
        if confirm2 != 'DELETE ALL':
            print("操作已取消")
            return False
        
        try:
            # 删除所有表
            from app.database import Base
            Base.metadata.drop_all(bind=engine)
            print("🗑️  所有表已删除")
            
            # 重新创建
            return self.init_database()
            
        except Exception as e:
            print(f"❌ 重置数据库失败: {e}")
            return False

def main():
    """主函数"""
    print("🔧 AI管理系统数据库迁移工具")
    print("=" * 60)
    
    manager = MigrationManager()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python migrate.py status         - 查看迁移状态")
        print("  python migrate.py init           - 初始化数据库") 
        print("  python migrate.py migrate        - 执行所有迁移")
        print("  python migrate.py migrate 001    - 执行到指定版本")
        print("  python migrate.py rollback 001   - 回滚指定迁移")
        print("  python migrate.py reset          - 重置数据库")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        manager.show_status()
        
    elif command == "init":
        manager.init_database()
        
    elif command == "migrate":
        target_version = sys.argv[2] if len(sys.argv) > 2 else None
        manager.run_migrations(target_version)
        
    elif command == "rollback":
        if len(sys.argv) < 3:
            print("❌ 请指定要回滚的版本号")
            return
        version = sys.argv[2]
        manager.rollback_migration(version)
        
    elif command == "reset":
        manager.reset_database()
        
    else:
        print(f"❌ 未知命令: {command}")

if __name__ == "__main__":
    main()