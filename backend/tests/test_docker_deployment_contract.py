from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_runtime_image_installs_linux_preview_dependencies() -> None:
    dockerfile = read_repo_file("Dockerfile").lower()

    required_packages = [
        "libreoffice",
        "libreoffice-math",
        "fonts-noto-cjk",
        "fonts-opensymbol",
        "fonts-stix",
        "fonts-dejavu-core",
        "fonts-wqy-zenhei",
        "fontconfig",
        "poppler-utils",
        "tini",
    ]
    missing = [package for package in required_packages if package not in dockerfile]

    assert not missing, f"Dockerfile missing runtime packages: {missing}"
    assert "sal_use_vclplugin=svp" in dockerfile
    assert "fc-cache" in dockerfile


def test_runtime_image_supports_fast_apt_mirrors() -> None:
    dockerfile = read_repo_file("Dockerfile")
    compose = read_repo_file("docker-compose.yml")
    env_example = read_repo_file(".env.example")

    assert "ARG APT_MIRROR" in dockerfile
    assert "ARG APT_SECURITY_MIRROR" in dockerfile
    assert "deb.debian.org/debian" in dockerfile
    assert "/etc/apt/sources.list.d/debian.sources" in dockerfile
    assert "bookworm-security" in dockerfile
    assert "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg" in dockerfile
    assert "sed -i" not in dockerfile
    assert "APT_MIRROR" in compose
    assert "APT_SECURITY_MIRROR" in compose
    assert "APT_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian" in env_example
    assert "APT_SECURITY_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian-security" in env_example


def test_healthchecks_use_backend_health_endpoint_through_nginx() -> None:
    dockerfile = read_repo_file("Dockerfile")
    compose = read_repo_file("docker-compose.yml")
    nginx = read_repo_file("backend/nginx.conf")

    assert "http://localhost:80/health" in dockerfile
    assert "http://localhost:80/health" in compose
    assert "location = /health" in nginx
    assert "proxy_pass http://127.0.0.1:8000" in nginx


def test_compose_uses_persistent_data_without_mounting_env_file() -> None:
    compose = read_repo_file("docker-compose.yml")

    assert "image: ${DOCSHOP_IMAGE:-docshop:latest}" in compose
    assert "./data:/app/data" in compose
    assert "./.env:/app/.env" not in compose
    assert "STORAGE_ROOT: /app/data" in compose
    assert "DATABASE_URL: sqlite:////app/data/docshop.db" in compose
    assert "UPLOAD_DIR: /app/data/uploads" in compose
    assert "LOG_DIR: /app/data/logs" in compose
    assert "TEMP_DIR: /app/data/temp" in compose
    assert "MOBILE_MODEL_CACHE_DIR: /app/data/cache" in compose
    assert "SECRET_KEY: ${SECRET_KEY:-auto}" in compose
    assert '"${DOCSHOP_PORT:-8080}:80"' in compose


def test_runtime_defaults_keep_storage_under_writable_app_data() -> None:
    dockerfile = read_repo_file("Dockerfile")
    start_script = read_repo_file("backend/start.sh")

    assert "STORAGE_ROOT=/app/data" in dockerfile
    assert "MOBILE_MODEL_CACHE_DIR=/app/data/cache" in dockerfile
    assert 'export STORAGE_ROOT="${STORAGE_ROOT:-/app/data}"' in start_script
    assert 'export MOBILE_MODEL_CACHE_DIR="${MOBILE_MODEL_CACHE_DIR:-/app/data/cache}"' in start_script
    assert "/app/data/objects" in start_script
    assert "/app/data/documents" in start_script
    assert "/app/data/trash" in start_script


def test_compose_exposes_preview_tuning_environment() -> None:
    compose = read_repo_file("docker-compose.yml")

    assert "DOCX2PDF_TIMEOUT_SECONDS" in compose
    assert "PREVIEW_PDF_TIMEOUT_SECONDS" in compose
    assert "PREVIEW_IMAGE_MAX_WORKERS" in compose
    assert "UVICORN_WORKERS" in compose


def test_container_start_script_handles_child_process_lifecycle() -> None:
    start_script = read_repo_file("backend/start.sh")

    assert "set -Eeuo pipefail" in start_script
    assert "trap" in start_script
    assert "wait -n" in start_script
    assert "nginx -g" in start_script
    assert "uvicorn app.main:app" in start_script


def test_container_start_script_migrates_legacy_docdist_database() -> None:
    start_script = read_repo_file("backend/start.sh")

    assert "/app/data/docshop.db" in start_script
    assert "/app/data/docdist.db" in start_script
    assert "docdist.db -> /app/data/docshop.db" in start_script
    assert "/app/scripts/migrate_sqlite_layout.py" in start_script


def test_container_start_script_migrates_legacy_backend_data_database_without_overwrite() -> None:
    start_script = read_repo_file("backend/start.sh")
    dockerfile = read_repo_file("Dockerfile")

    assert "/app/backend/data/docshop.db" in start_script
    assert "not overwrite" in start_script
    assert "migrate_sqlite_layout.py" in dockerfile


def test_container_start_script_generates_ephemeral_secret_key() -> None:
    start_script = read_repo_file("backend/start.sh")

    assert '${SECRET_KEY:-}' in start_script
    assert '"${SECRET_KEY:-}" == "auto"' in start_script
    assert "secrets.token_hex(32)" in start_script
    assert "generated ephemeral SECRET_KEY" in start_script
    assert "print(secrets.token_hex(32))" in start_script
    assert "echo \"$SECRET_KEY\"" not in start_script


def test_env_example_documents_docker_required_values() -> None:
    env_example = read_repo_file(".env.example")

    assert "SECRET_KEY=auto" in env_example
    assert "new random key on every container start" in env_example
    assert "DOCSHOP_PORT=8080" in env_example
    assert "DOCSHOP_IMAGE=docshop:latest" in env_example
    assert "DATABASE_URL=sqlite:////app/data/docshop.db" in env_example
    assert "DOCX2PDF_TIMEOUT_SECONDS=300" in env_example
    assert "PREVIEW_PDF_TIMEOUT_SECONDS=300" in env_example
    assert "PREVIEW_IMAGE_MAX_WORKERS=1" in env_example


def test_docker_build_script_auto_selects_base_image_mirror() -> None:
    build_script = read_repo_file("scripts/docker-build.ps1")
    up_script = read_repo_file("scripts/docker-up.ps1")
    vps_script = read_repo_file("scripts/vps-build.sh")
    env_example = read_repo_file(".env.example")

    assert "DOCKER_BASE_MIRROR" in build_script
    assert "NODE_IMAGE" in build_script
    assert "PYTHON_IMAGE" in build_script
    assert "registry-1.docker.io" in build_script
    assert "$_.Exception.Response" in build_script
    assert "docker.m.daocloud.io/library" in build_script
    assert "registry.cn-hangzhou.aliyuncs.com/library" in build_script
    assert "DOCKER_BASE_MIRROR" in up_script
    assert "docker.m.daocloud.io/library" in up_script
    assert "registry.cn-hangzhou.aliyuncs.com/library" in up_script
    assert "DOCKER_BASE_MIRROR" in vps_script
    assert "docker.m.daocloud.io/library" in vps_script
    assert "registry.cn-hangzhou.aliyuncs.com/library" in vps_script
    assert "DOCKER_BASE_MIRROR=" in env_example
    assert "registry.cn-hangzhou.aliyuncs.com/library" in env_example


def test_docker_base_mirror_selection_is_mirror_first_and_latency_aware() -> None:
    build_script = read_repo_file("scripts/docker-build.ps1")
    up_script = read_repo_file("scripts/docker-up.ps1")
    vps_script = read_repo_file("scripts/vps-build.sh")
    env_example = read_repo_file(".env.example")

    for script in [build_script, up_script]:
        assert "DOCKER_MIRROR_CANDIDATES" in script
        assert "DOCKER_MIRROR_TIMEOUT_SECONDS" in script
        assert "Normalize-DockerMirrorPrefix" in script
        assert "Select-FastestDockerMirror" in script
        assert "Measure-DockerRegistryLatency" in script
        assert "DOCKER_BASE_MIRROR=off" in script
        assert "registry-1.docker.io" in script

    assert "DOCKER_MIRROR_CANDIDATES" in vps_script
    assert "DOCKER_MIRROR_TIMEOUT_SECONDS" in vps_script
    assert "normalize_docker_mirror_prefix" in vps_script
    assert "docker_mirror_timeout_seconds" in vps_script
    assert "select_fastest_docker_mirror" in vps_script
    assert "measure_docker_registry_latency" in vps_script
    assert "DOCKER_BASE_MIRROR=off" in vps_script
    assert "registry-1.docker.io" in vps_script

    assert "DOCKER_MIRROR_CANDIDATES=" in env_example
    assert "DOCKER_MIRROR_TIMEOUT_SECONDS=2" in env_example


def test_docker_docs_describe_mirror_first_selection_not_official_first() -> None:
    env_example = read_repo_file(".env.example")
    readme = read_repo_file("README.md")
    docker_doc = read_repo_file("docs/docker-deployment.md")

    for document in [env_example, readme, docker_doc]:
        assert "DOCKER_MIRROR_CANDIDATES" in document
        assert "DOCKER_MIRROR_TIMEOUT_SECONDS" in document
        assert "先探测 Docker Hub" not in document
        assert "探测 Docker Hub，不可达" not in document

    assert "默认优先从候选镜像源中测速选择最快源" in env_example
    assert "默认优先从候选镜像源中测速选择最快源" in docker_doc
    assert "默认不先走 Docker Hub" in readme


def test_deploy_scripts_allow_auto_secret_key() -> None:
    deploy_script = read_repo_file("scripts/deploy.sh")
    vps_script = read_repo_file("scripts/vps-build.sh")

    assert 'SECRET_KEY=auto' in deploy_script
    assert "set SECRET_KEY first" not in deploy_script
    assert "SECRET_KEY is missing or too short" not in deploy_script
    assert 'SECRET_KEY=auto' in vps_script
    assert '"${secret_key}" != "auto"' in vps_script



def test_readme_documents_prod_and_dev_docker_workflows() -> None:
    readme = read_repo_file("README.md")

    assert "docker compose up -d --build" in readme
    assert "docker compose -f docker-compose.dev.yml up -d --build" in readme
    assert "docker compose logs -f docshop" in readme
    assert "docker compose -f docker-compose.dev.yml logs -f backend frontend" in readme
    assert "./data:/app/data" in readme
    assert "./frontend:/frontend" in readme
    assert "./backend/app:/app/app" in readme
    assert "LibreOffice" in readme
    assert "PREVIEW_IMAGE_MAX_WORKERS" in readme
