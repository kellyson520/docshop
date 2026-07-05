"""
数据库迁移脚本：创建考试安排相关表。

用途：
    python backend/scripts/migrate_add_exam_tables.py
    python backend/scripts/migrate_add_exam_tables.py --verify
    python backend/scripts/migrate_add_exam_tables.py --rollback

说明：
    - 脚本会检查表是否已存在，避免重复创建。
    - 默认数据库路径为 data/docshop.db。
    - 回滚会删除 exam_schedules 和 exam_reminders，请先备份数据库。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


EXAM_TABLES = ("exam_schedules", "exam_reminders")


def get_database_path() -> str:
    """从 DATABASE_URL 或默认路径解析 SQLite 数据库路径。"""
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        raw_path = db_url.replace("sqlite:///", "", 1)
        if raw_path.startswith("./"):
            raw_path = raw_path[2:]
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        return str(path.resolve(strict=False))

    project_root = Path(__file__).resolve().parents[2]
    return str(project_root / "data" / "docshop.db")


def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """检查表是否存在。"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def create_exam_schedules_table(cursor: sqlite3.Cursor) -> None:
    """创建考试安排表和索引。"""
    cursor.execute(
        """
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
        """
    )
    for index_sql in [
        "CREATE INDEX idx_exam_schedules_start_time ON exam_schedules(start_time)",
        "CREATE INDEX idx_exam_schedules_end_time ON exam_schedules(end_time)",
        "CREATE INDEX idx_exam_schedules_project_id ON exam_schedules(project_id)",
        "CREATE INDEX idx_exam_schedules_status ON exam_schedules(status)",
        "CREATE INDEX idx_exam_status_time ON exam_schedules(status, start_time)",
        "CREATE INDEX idx_exam_project ON exam_schedules(project_id, status)",
    ]:
        cursor.execute(index_sql)
    print("  [+] 已创建表: exam_schedules")


def create_exam_reminders_table(cursor: sqlite3.Cursor) -> None:
    """创建考试提醒表和索引。"""
    cursor.execute(
        """
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
        """
    )
    for index_sql in [
        "CREATE INDEX idx_exam_reminders_exam_id ON exam_reminders(exam_id)",
        "CREATE INDEX idx_exam_reminders_user_id ON exam_reminders(user_id)",
        "CREATE INDEX idx_reminder_user_exam ON exam_reminders(user_id, exam_id)",
        "CREATE INDEX idx_reminder_triggered ON exam_reminders(is_triggered, is_dismissed)",
    ]:
        cursor.execute(index_sql)
    print("  [+] 已创建表: exam_reminders")


def migrate() -> None:
    """创建考试安排相关表。"""
    db_path = get_database_path()
    print("=" * 60)
    print("数据库迁移：创建考试安排表")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()

    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        print("请确认路径是否正确，或先启动应用创建数据库。")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        created_tables: list[str] = []
        skipped_tables: list[str] = []

        if check_table_exists(cursor, "exam_schedules"):
            skipped_tables.append("exam_schedules")
            print("  [=] 表已存在，跳过: exam_schedules")
        else:
            create_exam_schedules_table(cursor)
            created_tables.append("exam_schedules")

        if check_table_exists(cursor, "exam_reminders"):
            skipped_tables.append("exam_reminders")
            print("  [=] 表已存在，跳过: exam_reminders")
        else:
            create_exam_reminders_table(cursor)
            created_tables.append("exam_reminders")

        conn.commit()
        print()
        print("迁移完成")
        print(f"新增表: {', '.join(created_tables) if created_tables else '无'}")
        print(f"已存在表: {', '.join(skipped_tables) if skipped_tables else '无'}")

    except sqlite3.Error as exc:
        print(f"错误: 数据库操作失败: {exc}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()


def rollback() -> None:
    """删除考试安排相关表。"""
    db_path = get_database_path()
    print("=" * 60)
    print("回滚考试安排表")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print("警告: 此操作会删除 exam_schedules 和 exam_reminders 中的所有数据。")
    confirm = input("确认删除请输入 yes: ")
    if confirm.lower() != "yes":
        print("已取消回滚。")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS exam_reminders")
        cursor.execute("DROP TABLE IF EXISTS exam_schedules")
        conn.commit()
        print("回滚完成。")
    except sqlite3.Error as exc:
        print(f"错误: 数据库操作失败: {exc}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()


def verify() -> None:
    """检查考试安排相关表结构。"""
    db_path = get_database_path()
    print("=" * 60)
    print("检查考试安排表结构")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for table in EXAM_TABLES:
            exists = check_table_exists(cursor, table)
            print(f"{'[OK]' if exists else '[MISSING]'} {table}")
            if not exists:
                continue
            cursor.execute(f"PRAGMA table_info({table})")
            for _cid, name, type_, notnull, default, _pk in cursor.fetchall():
                nullable = "否" if notnull else "是"
                print(f"  - {name:<22} {type_:<14} 可空: {nullable} 默认: {default or ''}")
            print()
    except sqlite3.Error as exc:
        print(f"检查失败: {exc}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="创建考试安排相关数据库表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verify", action="store_true", help="检查表结构")
    parser.add_argument("--rollback", action="store_true", help="删除考试安排相关表")
    parser.add_argument("--db-path", type=str, help="指定 SQLite 数据库路径")
    args = parser.parse_args()

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
