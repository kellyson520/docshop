"""
数据库迁移脚本：为 document_files 表补充卡片展示字段。

用途：
    python backend/scripts/migrate_add_card_fields.py
    python backend/scripts/migrate_add_card_fields.py --verify
    python backend/scripts/migrate_add_card_fields.py --db-path data/docshop.db

说明：
    - 脚本会先检查字段是否已存在，避免重复添加。
    - 默认数据库路径为 data/docshop.db。
    - 运行前建议先备份数据库。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


CARD_COLUMNS = {
    "cover_image": "TEXT",
    "description": "TEXT",
    "display_name": "TEXT",
    "updated_at": "TEXT",
}


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


def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """检查指定表中是否存在指定字段。"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return column_name in {column[1] for column in cursor.fetchall()}


def migrate() -> None:
    """执行字段补充迁移。"""
    db_path = get_database_path()
    print("=" * 60)
    print("数据库迁移：补充 document_files 卡片字段")
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

        added_columns: list[str] = []
        skipped_columns: list[str] = []

        for column_name, column_type in CARD_COLUMNS.items():
            if check_column_exists(cursor, "document_files", column_name):
                skipped_columns.append(column_name)
                print(f"  [=] 字段已存在，跳过: {column_name}")
                continue

            cursor.execute(
                f"ALTER TABLE document_files ADD COLUMN {column_name} {column_type}"
            )
            added_columns.append(column_name)
            print(f"  [+] 已添加字段: {column_name} ({column_type})")

        conn.commit()

        print()
        print("=" * 60)
        print("迁移完成")
        print("=" * 60)
        print(f"新增字段: {', '.join(added_columns) if added_columns else '无'}")
        print(f"已存在字段: {', '.join(skipped_columns) if skipped_columns else '无'}")

    except sqlite3.Error as exc:
        print(f"错误: 数据库操作失败: {exc}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()


def rollback() -> None:
    """输出回滚说明。SQLite 旧版本不适合直接 DROP COLUMN。"""
    print("=" * 60)
    print("回滚说明")
    print("=" * 60)
    print("SQLite 旧版本不支持安全地直接删除字段。")
    print("如需回滚，请使用迁移前的数据库备份恢复，或手动重建表。")


def verify() -> None:
    """检查 document_files 表字段。"""
    db_path = get_database_path()
    print("=" * 60)
    print("检查 document_files 表结构")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(document_files)")
        columns = cursor.fetchall()
        existing_columns = {column[1] for column in columns}

        print(f"{'字段名':<24} {'类型':<16} {'可空':<8}")
        print("-" * 52)
        for _cid, name, type_, notnull, _default, _pk in columns:
            nullable = "否" if notnull else "是"
            print(f"{name:<24} {type_:<16} {nullable:<8}")

        print()
        print("目标字段检查:")
        for column_name in CARD_COLUMNS:
            status = "[OK]" if column_name in existing_columns else "[MISSING]"
            print(f"  {status} {column_name}")

    except sqlite3.Error as exc:
        print(f"检查失败: {exc}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="为 document_files 表补充卡片展示字段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verify", action="store_true", help="检查表结构")
    parser.add_argument("--rollback", action="store_true", help="显示回滚说明")
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
