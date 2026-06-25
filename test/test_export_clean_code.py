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
