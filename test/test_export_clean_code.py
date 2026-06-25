from pathlib import Path

from scripts.export_clean_code import (
    export_clean_code,
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
