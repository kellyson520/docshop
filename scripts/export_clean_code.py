from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
import os
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\lihuo\Desktop\新建文件夹 (2)")


EXCLUDED_DIR_NAMES = {
    ".git",
    ".codegraph",
    ".pytest_cache",
    "__tests__",
    "node_modules",
    "logs",
    "playwright-report",
    "test-results",
}

EXCLUDED_DIR_PATHS = {
    "test",
    "backend/tests",
    "frontend/e2e",
    "frontend/src/test",
    "frontend/dist",
    "artifacts/coverage",
    "docs",
}

EXCLUDED_FILE_NAMES = {
    "pytest.ini",
    ".coverage",
    "vitest.config.js",
    "playwright.config.js",
    "requirements-dev.txt",
    "requirements-loadtest.txt",
}

EXCLUDED_FILE_PATTERNS = [
    "*.spec.*",
    "*.test.*",
    "*.log",
    "*.pid",
    "*.zip",
    "*_test*.db",
    "_tmp*.db",
]

EXCLUDED_FILE_PATHS = {
    "backend/.coverage",
    "backend/pytest.ini",
    "probe_counter.db",
    "debug_preconvert.db",
    "test.db",
}


@dataclass
class ExportSummary:
    copied_files: int = 0
    skipped_files: int = 0
    skipped_dirs: int = 0
    failed_files: list[str] = field(default_factory=list)
    skipped_reasons: Counter[str] = field(default_factory=Counter)


def to_posix_relative(root: Path, target: Path) -> str:
    return target.relative_to(root).as_posix()


def should_exclude_dir(relative_dir: str) -> bool:
    parts = [part for part in relative_dir.split("/") if part]
    if not parts:
        return False
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    return relative_dir in EXCLUDED_DIR_PATHS


def should_exclude_file(relative_file: str) -> bool:
    path = Path(relative_file)
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if relative_file in EXCLUDED_FILE_PATHS:
        return True
    return any(fnmatch(path.name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def export_clean_code(source_dir: Path, output_dir: Path) -> ExportSummary:
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    reset_output_dir(output_dir)
    summary = ExportSummary()

    for current_dir, dirnames, filenames in os.walk(source_dir):
        current_path = Path(current_dir)
        relative_dir = to_posix_relative(source_dir, current_path) if current_path != source_dir else ""

        kept_dirnames = []
        for dirname in dirnames:
            child_relative = "/".join(filter(None, [relative_dir, dirname]))
            if should_exclude_dir(child_relative):
                summary.skipped_dirs += 1
                summary.skipped_reasons["dir"] += 1
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        destination_dir = output_dir / relative_dir if relative_dir else output_dir
        destination_dir.mkdir(parents=True, exist_ok=True)

        for filename in filenames:
            relative_file = "/".join(filter(None, [relative_dir, filename]))
            if should_exclude_file(relative_file):
                summary.skipped_files += 1
                summary.skipped_reasons["file"] += 1
                continue

            source_file = current_path / filename
            target_file = destination_dir / filename
            try:
                shutil.copy2(source_file, target_file)
            except OSError:
                summary.failed_files.append(relative_file)
                continue
            summary.copied_files += 1

    return summary


def write_summary_file(output_dir: Path, source_dir: Path, summary: ExportSummary) -> Path:
    summary_path = output_dir / "export_summary.txt"
    lines = [
        f"Source: {Path(source_dir).resolve()}",
        f"Output: {Path(output_dir).resolve()}",
        f"Copied files: {summary.copied_files}",
        f"Skipped files: {summary.skipped_files}",
        f"Skipped directories: {summary.skipped_dirs}",
        "Skipped reasons:",
    ]

    if summary.skipped_reasons:
        for key, value in sorted(summary.skipped_reasons.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none: 0")

    lines.append("Failed files:")
    if summary.failed_files:
        lines.extend(f"- {item}" for item in summary.failed_files)
    else:
        lines.append("- none")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export deployable clean code from docshop.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = export_clean_code(args.source, args.output)
        write_summary_file(args.output, args.source, summary)
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1

    print(f"Source: {Path(args.source).resolve()}")
    print(f"Output: {Path(args.output).resolve()}")
    print(f"Copied files: {summary.copied_files}")
    print(f"Skipped files: {summary.skipped_files}")
    print(f"Skipped directories: {summary.skipped_dirs}")
    print(f"Failed files: {len(summary.failed_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
