from app.services.archive_analysis_service import build_archive_manifest, diff_archive_manifests


def test_build_archive_manifest_summarizes_root_nodes():
    manifest = build_archive_manifest(
        [
            {"path": "docs/readme.txt", "size": 12},
            {"path": "video/demo.mp4", "size": 34},
        ]
    )

    assert manifest["analysis_type"] == "archive_manifest"
    assert manifest["entry_count"] == 2
    assert manifest["root_nodes"] == ["docs", "video"]


def test_diff_archive_manifests_counts_added_and_removed_paths():
    previous = {
        "entries": [
            {"path": "docs/readme.txt"},
            {"path": "images/old.png"},
        ]
    }
    current = {
        "entries": [
            {"path": "docs/readme.txt"},
            {"path": "video/new.mp4"},
        ]
    }

    diff = diff_archive_manifests(previous, current)

    assert diff["files_added"] == 1
    assert diff["files_removed"] == 1
    assert diff["added_paths"] == ["video/new.mp4"]
    assert diff["removed_paths"] == ["images/old.png"]
