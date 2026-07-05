# Clean Code Export Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python exporter that copies deployable code from `C:\Users\lihuo\Desktop\docshop` into `C:\Users\lihuo\Desktop\新建文件夹 (2)` while removing tests and deployment-irrelevant files, and clearing the output directory before each export.

**Architecture:** Implement a single focused script at `scripts/export_clean_code.py` using standard-library modules only (`argparse`, `fnmatch`, `pathlib`, `shutil`, `collections`, `dataclasses`). Keep the copy logic testable by exposing small pure helpers for path matching and a single orchestration function for directory reset, tree copy, and summary generation. Verify behavior through root-level pytest tests in `test/`, using temporary directories instead of the real project tree.

**Tech Stack:** Python 3, pytest, pathlib, shutil, fnmatch, argparse

---

## File Structure

### Create

- `scripts/export_clean_code.py`
  - CLI entry point
  - default source/output paths
  - exclusion rules
  - helper functions for path normalization and exclusion checks
  - output directory reset
  - export execution
  - summary text generation

- `test/test_export_clean_code.py`
  - helper rule-matching tests
  - output reset tests
  - export integration tests against temporary directories
  - summary file assertions

### Modify

- None required for the first implementation

## Implementation Notes

- Keep all production code inside `scripts/export_clean_code.py`; do not spread this into backend/frontend packages.
- Prefer `Path` objects end-to-end to handle Chinese paths and spaces reliably.
- Use relative-path matching with POSIX-style separators (`/`) after normalization.
- Treat exclusion rules as data, not chained ad-hoc `if` statements.
- Preserve relative directory structure in the exported output.
- If one file copy fails, record the failure and continue; if the source root is missing or the output root cannot be reset, exit with a non-zero status.

## Task 1: Build and verify exclusion-rule helpers

**Files:**
- Create: `test/test_export_clean_code.py`
- Create: `scripts/export_clean_code.py`
- Test: `test/test_export_clean_code.py`

- [ ] **Step 1: Write the failing tests for rule matching**

Create `test/test_export_clean_code.py` with these tests first:

```python
from pathlib import Path

from scripts.export_clean_code import (
    should_exclude_dir,
    should_exclude_file,
    to_posix_relative,
)


def test_to_posix_relative_normalizes_windows_like_paths():
    root = Path("C:/repo")
    target = Path("C:/repo/frontend/src/__tests__/demo.spec.js")

    assert to_posix_relative(root, target) == "frontend/src/__tests__/demo.spec.js"


def test_should_exclude_dir_for_known_test_and_noise_directories():
    assert should_exclude_dir("backend/tests") is True
    assert should_exclude_dir("frontend/src/components/__tests__") is True
    assert should_exclude_dir("frontend/node_modules") is True
    assert should_exclude_dir("docs") is True
    assert should_exclude_dir("frontend/src/components") is False


def test_should_exclude_file_for_test_and_noise_files():
    assert should_exclude_file("frontend/e2e/auth.spec.js") is True
    assert should_exclude_file("frontend/src/utils/preview.test.js") is True
    assert should_exclude_file("frontend/vitest.config.js") is True
    assert should_exclude_file("backend/requirements-dev.txt") is True
    assert should_exclude_file("backend/dev-backend.log") is True
    assert should_exclude_file("frontend/src/main.js") is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
FAIL test/test_export_clean_code.py::test_to_posix_relative_normalizes_windows_like_paths
FAIL test/test_export_clean_code.py::test_should_exclude_dir_for_known_test_and_noise_directories
FAIL test/test_export_clean_code.py::test_should_exclude_file_for_test_and_noise_files
E   ModuleNotFoundError: No module named 'scripts.export_clean_code'
```

- [ ] **Step 3: Write the minimal production code to satisfy the helper tests**

Create `scripts/export_clean_code.py` with this initial implementation:

```python
from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


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
```

- [ ] **Step 4: Run the helper tests to verify they pass**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
PASS test/test_export_clean_code.py::test_to_posix_relative_normalizes_windows_like_paths
PASS test/test_export_clean_code.py::test_should_exclude_dir_for_known_test_and_noise_directories
PASS test/test_export_clean_code.py::test_should_exclude_file_for_test_and_noise_files
```

- [ ] **Step 5: Commit the helper-rule slice**

Run:

```bash
git add test/test_export_clean_code.py scripts/export_clean_code.py
git commit -m "test: add clean export exclusion rule coverage"
```

## Task 2: Add output reset and directory export behavior

**Files:**
- Modify: `test/test_export_clean_code.py`
- Modify: `scripts/export_clean_code.py`
- Test: `test/test_export_clean_code.py`

- [ ] **Step 1: Write failing tests for output reset and copy behavior**

Append these tests to `test/test_export_clean_code.py`:

```python
from scripts.export_clean_code import export_clean_code


def test_export_clean_code_clears_output_before_copy(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "导出 目录"
    source.mkdir()
    output.mkdir()

    (output / "stale.txt").write_text("old", encoding="utf-8")
    (source / "frontend").mkdir()
    (source / "frontend" / "src").mkdir()
    (source / "frontend" / "src" / "main.js").write_text("console.log('ok')", encoding="utf-8")

    summary = export_clean_code(source, output)

    assert summary.copied_files == 1
    assert (output / "stale.txt").exists() is False
    assert (output / "frontend" / "src" / "main.js").read_text(encoding="utf-8") == "console.log('ok')"


def test_export_clean_code_skips_noise_and_preserves_relative_structure(tmp_path):
    source = tmp_path / "project root"
    output = tmp_path / "clean output"
    source.mkdir()

    (source / "backend").mkdir()
    (source / "backend" / "app").mkdir()
    (source / "backend" / "app" / "main.py").write_text("app = 'ok'", encoding="utf-8")
    (source / "backend" / "tests").mkdir()
    (source / "backend" / "tests" / "test_api.py").write_text("assert False", encoding="utf-8")
    (source / "frontend").mkdir()
    (source / "frontend" / "src").mkdir()
    (source / "frontend" / "src" / "__tests__").mkdir()
    (source / "frontend" / "src" / "__tests__" / "demo.spec.js").write_text("bad", encoding="utf-8")
    (source / "frontend" / "src" / "App.vue").write_text("<template />", encoding="utf-8")
    (source / "docs").mkdir()
    (source / "docs" / "readme.md").write_text("drop", encoding="utf-8")
    (source / "frontend" / "vite.config.js").write_text("keep", encoding="utf-8")
    (source / "frontend" / "vitest.config.js").write_text("drop", encoding="utf-8")

    summary = export_clean_code(source, output)

    assert (output / "backend" / "app" / "main.py").exists() is True
    assert (output / "frontend" / "src" / "App.vue").exists() is True
    assert (output / "frontend" / "vite.config.js").exists() is True
    assert (output / "backend" / "tests").exists() is False
    assert (output / "frontend" / "src" / "__tests__").exists() is False
    assert (output / "docs").exists() is False
    assert (output / "frontend" / "vitest.config.js").exists() is False
    assert summary.skipped_dirs >= 3
    assert summary.skipped_files >= 1
```

- [ ] **Step 2: Run the tests to verify they fail for the expected reason**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
FAIL test/test_export_clean_code.py::test_export_clean_code_clears_output_before_copy
FAIL test/test_export_clean_code.py::test_export_clean_code_skips_noise_and_preserves_relative_structure
E   ImportError: cannot import name 'export_clean_code' from 'scripts.export_clean_code'
```

- [ ] **Step 3: Add the export summary model and tree-copy implementation**

Replace `scripts/export_clean_code.py` with:

```python
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
import shutil


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

    for current_dir, dirnames, filenames in __import__("os").walk(source_dir):
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
            shutil.copy2(source_file, target_file)
            summary.copied_files += 1

    return summary
```

- [ ] **Step 4: Run the tests to verify export behavior passes**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
PASS test/test_export_clean_code.py::test_export_clean_code_clears_output_before_copy
PASS test/test_export_clean_code.py::test_export_clean_code_skips_noise_and_preserves_relative_structure
```

- [ ] **Step 5: Commit the export behavior slice**

Run:

```bash
git add test/test_export_clean_code.py scripts/export_clean_code.py
git commit -m "feat: add clean code export copy workflow"
```

## Task 3: Add summary output, failure tracking, and CLI entry point

**Files:**
- Modify: `test/test_export_clean_code.py`
- Modify: `scripts/export_clean_code.py`
- Test: `test/test_export_clean_code.py`

- [ ] **Step 1: Write failing tests for summary file generation and CLI defaults**

Append these tests to `test/test_export_clean_code.py`:

```python
import subprocess
import sys

from scripts.export_clean_code import DEFAULT_OUTPUT_DIR, DEFAULT_SOURCE_DIR, write_summary_file


def test_write_summary_file_contains_expected_sections(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    summary = ExportSummary(
        copied_files=3,
        skipped_files=2,
        skipped_dirs=1,
        failed_files=["frontend/src/bad.js"],
    )
    summary.skipped_reasons.update({"dir": 1, "file": 2})

    summary_path = write_summary_file(output, DEFAULT_SOURCE_DIR, summary)
    text = summary_path.read_text(encoding="utf-8")

    assert summary_path.name == "export_summary.txt"
    assert "Source:" in text
    assert "Output:" in text
    assert "Copied files: 3" in text
    assert "Skipped files: 2" in text
    assert "Skipped directories: 1" in text
    assert "frontend/src/bad.js" in text


def test_cli_uses_explicit_source_and_output_arguments(tmp_path):
    source = tmp_path / "source repo"
    output = tmp_path / "部署 目录"
    source.mkdir()
    (source / "backend").mkdir()
    (source / "backend" / "app.py").write_text("print('ok')", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_clean_code.py",
            "--source",
            str(source),
            "--output",
            str(output),
        ],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (output / "backend" / "app.py").exists() is True
    assert (output / "export_summary.txt").exists() is True
    assert "Copied files:" in result.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
FAIL test/test_export_clean_code.py::test_write_summary_file_contains_expected_sections
FAIL test/test_export_clean_code.py::test_cli_uses_explicit_source_and_output_arguments
E   ImportError: cannot import name 'DEFAULT_OUTPUT_DIR' from 'scripts.export_clean_code'
```

- [ ] **Step 3: Add summary writer, CLI parsing, and resilient file-copy tracking**

Update `scripts/export_clean_code.py` to:

```python
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
import argparse
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
```

- [ ] **Step 4: Run the tests to verify the CLI and summary behavior passes**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
PASS test/test_export_clean_code.py::test_write_summary_file_contains_expected_sections
PASS test/test_export_clean_code.py::test_cli_uses_explicit_source_and_output_arguments
```

- [ ] **Step 5: Commit the CLI slice**

Run:

```bash
git add test/test_export_clean_code.py scripts/export_clean_code.py
git commit -m "feat: add clean code export cli and summary"
```

## Task 4: Run final verification on the new utility

**Files:**
- Modify: none
- Test: `test/test_export_clean_code.py`

- [ ] **Step 1: Run the focused pytest file**

Run:

```bash
python -m pytest test/test_export_clean_code.py -v
```

Expected:

```text
===== 7 passed in
```

- [ ] **Step 2: Run the full root pytest suite**

Run:

```bash
python -m pytest -v
```

Expected:

```text
================= ... passed, 0 failed =================
```

- [ ] **Step 3: Dry-run the exporter against the real project paths**

Run:

```bash
python scripts/export_clean_code.py --source "C:\Users\lihuo\Desktop\docshop" --output "C:\Users\lihuo\Desktop\新建文件夹 (2)"
```

Expected:

```text
Source: C:\Users\lihuo\Desktop\docshop
Output: C:\Users\lihuo\Desktop\新建文件夹 (2)
Copied files:
Skipped files:
Skipped directories:
Failed files: 0
```

- [ ] **Step 4: Spot-check the output tree**

Run:

```bash
Get-ChildItem -Recurse "C:\Users\lihuo\Desktop\新建文件夹 (2)" | Select-Object FullName
```

Expected:

```text
Contains backend/app, frontend/src, scripts, Docker/compose files, export_summary.txt
Does not contain backend/tests, frontend/e2e, __tests__, docs, logs, *.spec.*, *.test.*, *.log, *.pid
```

- [ ] **Step 5: Commit the verified utility**

Run:

```bash
git add scripts/export_clean_code.py test/test_export_clean_code.py
git commit -m "feat: add deployable clean code export tool"
```

## Spec Coverage Checklist

- Source and output paths defined: covered by Task 3 CLI defaults and explicit argument support.
- Remove tests and deployment-irrelevant content: covered by Task 1 rule helpers and Task 2 export integration tests.
- Clear output directory before each run: covered by Task 2 reset test and implementation.
- Preserve deployable source/config/script files: covered by Task 2 integration assertions and Task 4 spot-check.
- Summary output: covered by Task 3 summary-file test and CLI output.
- Chinese/space paths: covered by Task 2 and Task 3 tests using `导出 目录`, `project root`, and `部署 目录`.
- Failure recording: covered by Task 3 `failed_files` support and summary content.

## Self-Review Notes

- No placeholder markers remain.
- All tasks use exact file paths.
- Test-first order is preserved in every task.
- The plan stays inside the agreed scope: export utility only, no auto-install/build/zip features.
