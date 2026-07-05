def build_archive_manifest(entries: list[dict]) -> dict:
    normalized_entries = [
        {
            "path": str(entry.get("path") or "").strip("/"),
            "size": int(entry.get("size") or 0),
        }
        for entry in entries
        if entry.get("path")
    ]
    root_nodes = sorted({item["path"].split("/", 1)[0] for item in normalized_entries if item["path"]})
    return {
        "analysis_type": "archive_manifest",
        "entry_count": len(normalized_entries),
        "root_nodes": root_nodes,
        "entries": normalized_entries,
    }


def diff_archive_manifests(previous: dict, current: dict) -> dict:
    previous_paths = {str(entry.get("path") or "").strip("/") for entry in previous.get("entries", []) if entry.get("path")}
    current_paths = {str(entry.get("path") or "").strip("/") for entry in current.get("entries", []) if entry.get("path")}
    added_paths = sorted(current_paths - previous_paths)
    removed_paths = sorted(previous_paths - current_paths)
    return {
        "files_added": len(added_paths),
        "files_removed": len(removed_paths),
        "added_paths": added_paths,
        "removed_paths": removed_paths,
    }
