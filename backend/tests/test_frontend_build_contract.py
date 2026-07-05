from pathlib import Path


def test_vite_build_explicitly_disables_sourcemaps():
    repo_root = Path(__file__).resolve().parents[2]
    vite_config = (repo_root / "frontend" / "vite.config.js").read_text(encoding="utf-8")

    assert "sourcemap: false" in vite_config
