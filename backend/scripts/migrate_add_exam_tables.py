"""
数据库迁移脚本：创建考试安排相关表

此脚本用于向现有数据库添加考试安排功能所需的表：
- exam_schedules: 考试安排表
- exam_reminders: 考试提醒记录表

使用方法:
    python scripts/migrate_add_exam_tables.py

注意事项:
    - 请在执行前备份数据库
    - 脚本会检查表是否已存在，避免重复创建
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


def check_table_exists(cursor, table_name: str) -> bool:
    """
    检查表是否存在

    Args:
        cursor: 数据库游标
        table_name: 表名

    Returns:
        bool: 表存在返回 True
    """
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def create_exam_schedules_table(cursor):
    """
    创建考试安排表

    Args:
        cursor: 数据库游标
    """
    cursor.execute("""
        CREATE TABLE exam_schedules (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            start_time VARCHAR(30) NOT NULL,
            end_time VARCHAR(30) NOT NULL,
            project_id VARCHAR(36) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
            reminder_15min INTEGER NOT NULL DEFAULT 1,
            reminder_5min INTEGER NOT NULL DEFAULT 1,
            reminder_start INTEGER NOT NULL DEFAULT 1,
            created_by VARCHAR(36) NOT NULL,
            created_at VARCHAR(30) NOT NULL,
            updated_at VARCHAR(30) NOT NULL
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX idx_exam_schedules_start_time ON exam_schedules(start_time)
    """)
    cursor.execute("""
        CREATE INDEX idx_exam_schedules_end_time ON exam_schedules(end_time)
    """)
    cursor.execute("""
        CREATE INDEX idx_exam_schedules_project_id ON exam_schedules(project_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_exam_schedules_status ON exam_schedules(status)
    """)
    cursor.execute("""
        CREATE INDEX idx_exam_status_time ON exam_schedules(status, start_time)
    """)
    cursor.execute("""
        CREATE INDEX idx_exam_project ON exam_schedules(project_id, status)
    """)

    print("  [+] 创建表: exam_schedules")
    print("  [+] 创建索引: idx_exam_schedules_start_time")
    print("  [+] 创建索引: idx_exam_schedules_end_time")
    print("  [+] 创建索引: idx_exam_schedules_project_id")
    print("  [+] 创建索引: idx_exam_schedules_status")
    print("  [+] 创建索引: idx_exam_status_time")
    print("  [+] 创建索引: idx_exam_project")


def create_exam_reminders_table(cursor):
    """
    创建考试提醒记录表

    Args:
        cursor: 数据库游标
    """
    cursor.execute("""
        CREATE TABLE exam_reminders (
            id VARCHAR(36) PRIMARY KEY,
            exam_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            reminder_type VARCHAR(20) NOT NULL,
            is_triggered INTEGER NOT NULL DEFAULT 0,
            is_dismissed INTEGER NOT NULL DEFAULT 0,
            triggered_at VARCHAR(30),
            dismissed_at VARCHAR(30),
            created_at VARCHAR(30) NOT NULL
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX idx_exam_reminders_exam_id ON exam_reminders(exam_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_exam_reminders_user_id ON exam_reminders(user_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_reminder_user_exam ON exam_reminders(user_id, exam_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_reminder_triggered ON exam_reminders(is_triggered, is_dismissed)
    """)

    print("  [+] 创建表: exam_reminders")
    print("  [+] 创建索引: idx_exam_reminders_exam_id")
    print("  [+] 创建索引: idx_exam_reminders_user_id")
    print("  [+] 创建索引: idx_reminder_user_exam")
    print("  [+] 创建索引: idx_reminder_triggered")


def migrate():
    """
    执行数据库迁移

    创建考试安排相关的表和索引。
    """
    db_path = get_database_path()

    print(f"=" * 60)
    print(f"数据库迁移脚本 - 创建考试安排表")
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

        print("正在检查现有表...")
        print()

        created_tables = []
        skipped_tables = []

        # 检查并创建 exam_schedules 表
        if not check_table_exists(cursor, 'exam_schedules'):
            create_exam_schedules_table(cursor)
            created_tables.append('exam_schedules')
        else:
            skipped_tables.append('exam_schedules')
            print("  [=] 表已存在，跳过: exam_schedules")

        print()

        # 检查并创建 exam_reminders 表
        if not check_table_exists(cursor, 'exam_reminders'):
            create_exam_reminders_table(cursor)
            created_tables.append('exam_reminders')
        else:
            skipped_tables.append('exam_reminders')
            print("  [=] 表已存在，跳过: exam_reminders")

        # 提交事务
        conn.commit()

        print()
        print("=" * 60)
        print("迁移结果")
        print("=" * 60)

        if created_tables:
            print(f"成功创建表: {', '.join(created_tables)}")
        else:
            print("没有新表需要创建")

        if skipped_tables:
            print(f"已存在的表: {', '.join(skipped_tables)}")

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
    回滚迁移

    删除考试安排相关的表。
    警告: 此操作会删除所有考试数据！
    """
    db_path = get_database_path()

    print("=" * 60)
    print("回滚迁移 - 删除考试安排表")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()
    print("警告: 此操作将删除以下表及其所有数据:")
    print("  - exam_schedules")
    print("  - exam_reminders")
    print()

    confirm = input("确认删除? 请输入 'yes' 继续: ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 删除表（SQLite 会自动删除关联的索引）
        cursor.execute("DROP TABLE IF EXISTS exam_reminders")
        print("  [-] 删除表: exam_reminders")

        cursor.execute("DROP TABLE IF EXISTS exam_schedules")
        print("  [-] 删除表: exam_schedules")

        conn.commit()

        print()
        print("回滚完成！")

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


def verify():
    """
    验证迁移结果

    检查考试安排相关的表结构。
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

        # 检查表是否存在
        tables = ['exam_schedules', 'exam_reminders']

        print("表检查:")
        for table in tables:
            exists = check_table_exists(cursor, table)
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {table}")

        print()

        # 显示表结构
        for table in tables:
            if check_table_exists(cursor, table):
                print(f"{table} 表结构:")
                print("-" * 60)

                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()

                print(f"{'字段名':<20} {'类型':<15} {'可空':<10} {'默认值':<15}")
                print("-" * 60)

                for col in columns:
                    cid, name, type_, notnull, dflt_value, pk = col
                    nullable = "NO" if notnull else "YES"
                    default = str(dflt_value) if dflt_value else ""
                    print(f"{name:<20} {type_:<15} {nullable:<10} {default:<15}")

                print("-" * 60)

                # 显示索引
                cursor.execute(f"PRAGMA index_list({table})")
                indexes = cursor.fetchall()
                if indexes:
                    print("索引:")
                    for idx in indexes:
                        seq, name, unique, origin, partial = idx
                        unique_str = "UNIQUE" if unique else ""
                        print(f"  - {name} {unique_str}")
                print()

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
        description="数据库迁移脚本 - 创建考试安排表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python migrate_add_exam_tables.py           # 执行迁移
  python migrate_add_exam_tables.py --verify  # 验证迁移结果
  python migrate_add_exam_tables.py --rollback # 回滚迁移（删除表）
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
        help='回滚迁移（删除表）'
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
