"""
数据库迁移脚本：添加卡片相关字段

此脚本用于向现有数据库的 document_files 表中添加卡片式文档管理所需的字段：
- cover_image: 封面图片路径
- description: 文件介绍
- display_name: 显示名称
- updated_at: 更新时间

使用方法:
    python scripts/migrate_add_card_fields.py

注意事项:
    - 请在执行前备份数据库
    - 脚本会检查字段是否已存在，避免重复添加
    - 默认数据库路径: data/docdist.db
"""

import sqlite3
import sys
import os
from pathlib import Path


def get_database_path() -> str:
    """
    获取数据库路径
    
    优先使用环境变量 DATABASE_URL，否则使用默认路径。
    
    Returns:
        str: 数据库文件路径
    """
    # 从环境变量获取
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        # 处理 sqlite:///./data/docdist.db 格式
        path = db_url.replace("sqlite:///", "")
        # 处理相对路径
        if path.startswith("./"):
            path = path[2:]
        return path
    
    # 默认路径
    backend_dir = Path(__file__).parent.parent
    return str(backend_dir / "data" / "docdist.db")


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """
    检查表中是否存在指定字段
    
    Args:
        cursor: 数据库游标
        table_name: 表名
        column_name: 字段名
        
    Returns:
        bool: 字段存在返回 True
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns


def migrate():
    """
    执行数据库迁移
    
    添加卡片相关字段到 document_files 表。
    """
    db_path = get_database_path()
    
    print(f"=" * 60)
    print(f"数据库迁移脚本")
    print(f"=" * 60)
    print(f"数据库路径: {db_path}")
    print()
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        print("请确认数据库路径是否正确，或先运行应用创建数据库。")
        sys.exit(1)
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("正在检查现有字段...")
        
        # 检查字段是否存在
        columns_to_add = {
            'cover_image': 'TEXT',
            'description': 'TEXT',
            'display_name': 'TEXT',
            'updated_at': 'TEXT',
        }
        
        added_columns = []
        skipped_columns = []
        
        for column_name, column_type in columns_to_add.items():
            if not check_column_exists(cursor, 'document_files', column_name):
                cursor.execute(
                    f"ALTER TABLE document_files ADD COLUMN {column_name} {column_type}"
                )
                added_columns.append(column_name)
                print(f"  [+] 添加字段: {column_name} ({column_type})")
            else:
                skipped_columns.append(column_name)
                print(f"  [=] 字段已存在，跳过: {column_name}")
        
        # 提交事务
        conn.commit()
        
        print()
        print("=" * 60)
        print("迁移结果")
        print("=" * 60)
        
        if added_columns:
            print(f"成功添加字段: {', '.join(added_columns)}")
        else:
            print("没有新字段需要添加")
        
        if skipped_columns:
            print(f"已存在的字段: {', '.join(skipped_columns)}")
        
        print()
        print("迁移完成！")
        
    except sqlite3.Error as e:
        print()
        print(f"错误: 数据库操作失败: {e}")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"错误: 发生未知错误: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


def rollback():
    """
    回滚迁移（SQLite 不支持 DROP COLUMN，此功能受限）
    
    注意: SQLite 3.35.0+ 才支持 DROP COLUMN。
    对于旧版本，需要使用表重建的方式回滚。
    """
    print("=" * 60)
    print("回滚迁移")
    print("=" * 60)
    print()
    print("警告: SQLite 不支持直接删除字段。")
    print("如需回滚，请手动重建表或使用数据库备份恢复。")
    print()
    print("建议操作:")
    print("1. 使用迁移前的数据库备份恢复")
    print("2. 或手动执行 SQL 重建表结构")


def verify():
    """
    验证迁移结果
    
    检查 document_files 表的字段结构。
    """
    db_path = get_database_path()
    
    print("=" * 60)
    print("验证迁移结果")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(document_files)")
        columns = cursor.fetchall()
        
        print("document_files 表结构:")
        print("-" * 60)
        print(f"{'字段名':<20} {'类型':<15} {'可空':<10}")
        print("-" * 60)
        
        for col in columns:
            cid, name, type_, notnull, dflt_value, pk = col
            nullable = "NO" if notnull else "YES"
            print(f"{name:<20} {type_:<15} {nullable:<10}")
        
        print("-" * 60)
        
        # 检查目标字段
        target_columns = ['cover_image', 'description', 'display_name', 'updated_at']
        existing_columns = [col[1] for col in columns]
        
        print()
        print("字段检查:")
        for col in target_columns:
            status = "[OK]" if col in existing_columns else "[MISSING]"
            print(f"  {status} {col}")
        
    except Exception as e:
        print(f"验证失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    """
    主函数
    
    根据命令行参数执行相应操作。
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="数据库迁移脚本 - 添加卡片相关字段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python migrate_add_card_fields.py           # 执行迁移
  python migrate_add_card_fields.py --verify  # 验证迁移结果
  python migrate_add_card_fields.py --rollback # 查看回滚说明
        """
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='验证迁移结果'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='显示回滚说明'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        help='指定数据库路径（覆盖默认路径）'
    )
    
    args = parser.parse_args()
    
    # 如果指定了数据库路径，设置环境变量
    if args.db_path:
        os.environ["DATABASE_URL"] = f"sqlite:///{args.db_path}"
    
    if args.verify:
        verify()
    elif args.rollback:
        rollback()
    else:
        migrate()


if __name__ == "__main__":
    main()
