from app.services.html_runtime_preview_service import build_runtime_html_preview


def test_build_runtime_html_preview_returns_direct_html_document_with_rewritten_assets(tmp_path):
    html_path = tmp_path / "interactive.html"
    html_path.write_text(
        (
            """<!DOCTYPE html><html><head><title>Interactive Demo</title>"""
            """<link rel="stylesheet" href="styles/app.css"></head>"""
            """<body><main>hello</main><script src="./app.js"></script></body></html>"""
        ),
        encoding="utf-8",
    )

    runtime_html = build_runtime_html_preview(
        storage_path=str(html_path),
        title="Interactive Demo",
        asset_url_resolver=lambda asset_path: f"/resolved/{asset_path.lstrip('./')}",
    )

    assert "URL.createObjectURL" not in runtime_html
    assert "location.replace(runtimeUrl)" not in runtime_html
    assert "<main>hello</main>" in runtime_html
    assert "/resolved/styles/app.css" in runtime_html
    assert "/resolved/app.js" in runtime_html
