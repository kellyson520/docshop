from app.schemas.diff_result import normalize_diff_result


def test_normalize_legacy_pdf_result_adds_canonical_sections_and_metrics():
    raw = {
        "type": "pdf_diff",
        "identical": False,
        "page_diffs": [{"page_number": 1, "change_type": "modified"}],
        "table_diffs": [{"page_number": 1, "table_index": 0}],
        "summary": "PDF changed",
        "stats": {"pages_modified": 1},
    }

    result = normalize_diff_result(raw, file_type="pdf", elapsed_ms=37, status="completed")

    assert set(["text", "tables", "images", "metadata", "summary", "stats"]).issubset(result)
    assert result["text"] == raw["page_diffs"]
    assert result["tables"] == raw["table_diffs"]
    assert result["images"] == {"added": [], "deleted": [], "replaced": [], "resized": []}
    assert result["metadata"]["file_type"] == "pdf"
    assert result["metadata"]["elapsed_ms"] == 37
    assert result["status"] == "completed"
    assert result["stats"]["text_changes"] == 1
    assert result["stats"]["tables_changed"] == 1
    assert result["stats"]["total_changes"] == 2
    assert result["changes"]["text"] == result["text"]


def test_normalize_docx_images_counts_added_deleted_replaced_resized():
    raw = {
        "type": "docx_diff",
        "paragraph_diffs": [{"type": "move", "old_index": 11, "new_index": 29}],
        "tables": [{"table_index": 0, "cell_changes": [{"row": 0, "col": 0}]}],
        "images": {
            "added": [{"filename": "new.png"}],
            "deleted": [{"filename": "old.png"}],
            "replaced": [{"old": {"sha256": "a"}, "new": {"sha256": "b"}}],
            "resized": [{"filename": "same.png"}],
        },
        "metadata": {"old_paragraph_count": 20},
    }

    result = normalize_diff_result(raw, file_type="docx")

    assert result["text"] == raw["paragraph_diffs"]
    assert result["tables"] == raw["tables"]
    assert result["stats"]["text_moves"] == 1
    assert result["stats"]["image_added"] == 1
    assert result["stats"]["image_deleted"] == 1
    assert result["stats"]["image_replaced"] == 1
    assert result["stats"]["image_resized"] == 1
    assert result["stats"]["total_changes"] == 6
    assert result["metadata"]["old_paragraph_count"] == 20
    assert result["metadata"]["file_type"] == "docx"


def test_normalize_error_result_keeps_error_and_status():
    result = normalize_diff_result({}, file_type="docx", status="failed", error="boom")

    assert result["status"] == "failed"
    assert result["error"] == "boom"
    assert result["summary"] == "差异计算失败"
    assert result["stats"]["total_changes"] == 0
