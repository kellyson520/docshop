from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_runtime_requirements_list_direct_import_dependencies() -> None:
    requirements = read_repo_file("backend/requirements.txt")

    required = [
        "Pillow",
        "numpy",
        'pywin32>=306; platform_system=="Windows"',
    ]
    missing = [item for item in required if item not in requirements]

    assert not missing, f"backend/requirements.txt missing direct runtime dependencies: {missing}"


def test_dependency_inventory_documents_required_layers() -> None:
    inventory = read_repo_file("docs/dependencies.md")

    required_phrases = [
        "Python runtime",
        "Node build",
        "Docker runtime system packages",
        "Optional Windows Word COM",
        "LibreOffice",
        "fonts-noto-cjk",
        "Pillow",
        "PyMuPDF",
        "poppler-utils",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in inventory]

    assert not missing, f"docs/dependencies.md missing sections/items: {missing}"


def test_deployment_docs_link_dependency_inventory() -> None:
    readme = read_repo_file("README.md")
    docker_docs = read_repo_file("docs/docker-deployment.md")

    assert "docs/dependencies.md" in readme
    assert "docs/dependencies.md" in docker_docs
