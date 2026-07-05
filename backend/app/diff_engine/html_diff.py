from __future__ import annotations

"""Semantic HTML diff engine.

This engine compares browser-facing structure rather than raw source bytes.
It deliberately drops scripts/styles/comments and emits bounded text snippets
instead of full uploaded HTML source.
"""

import difflib
import hashlib
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from app.diff_engine.base import BaseDiffEngine


SEMANTIC_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "a", "img",
    "button", "input", "select", "textarea",
    "table", "tr", "td", "th",
}
RESOURCE_ATTRIBUTES = {"href", "src"}
IMPORTANT_ATTRIBUTES = {
    "id", "class", "href", "src", "alt", "title", "name",
    "type", "value", "placeholder", "aria-label",
}
SKIP_TAGS = {"script", "style", "noscript"}


def _collapse_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _snippet(value: str | None, limit: int = 240) -> str:
    text = _collapse_text(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated]"


def _fingerprint(value: str | None) -> str:
    normalized = _collapse_text(value).lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12] if normalized else ""


def _normalize_attr_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return " ".join(sorted(_collapse_text(item) for item in value if _collapse_text(item)))
    return _collapse_text(value)


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["HtmlNode"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    parent: "HtmlNode | None" = None
    path: str = ""
    order: int = 0

    def append_text(self, value: str) -> None:
        text = _collapse_text(value)
        if text:
            self.text_parts.append(text)

    @property
    def text(self) -> str:
        parts = list(self.text_parts)
        for child in self.children:
            child_text = child.text
            if child_text:
                parts.append(child_text)
        if self.tag == "img":
            parts.extend([self.attrs.get("alt", ""), self.attrs.get("src", "")])
        if self.tag in {"input", "textarea", "button"}:
            parts.extend([
                self.attrs.get("value", ""),
                self.attrs.get("placeholder", ""),
                self.attrs.get("aria-label", ""),
            ])
        return _collapse_text(" ".join(parts))


class _HtmlTreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("document")
        self.stack: list[HtmlNode] = [self.root]
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        normalized_attrs = {
            key.lower(): _normalize_attr_value(value if value is not None else "")
            for key, value in attrs
            if key
        }
        node = HtmlNode(tag=tag, attrs=normalized_attrs, parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in {"br", "hr", "meta", "link", "img", "input"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.stack[-1].append_text(data)


class HtmlDiffEngine(BaseDiffEngine):
    """Semantic diff engine for HTML/HTM files."""

    def compare(self, old_path: str, new_path: str) -> dict[str, Any]:
        old_nodes = self._extract_nodes(old_path)
        new_nodes = self._extract_nodes(new_path)
        result = self._compare_nodes(old_nodes, new_nodes)
        return self._cap_diff_payload(result)

    def generate_summary(self, diff_data: dict) -> str:
        return str(diff_data.get("summary") or diff_data.get("summary_text") or "")

    def _extract_nodes(self, path: str) -> list[dict[str, Any]]:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            html = handle.read()
        parser = _HtmlTreeParser()
        parser.feed(html)
        nodes: list[dict[str, Any]] = []
        self._assign_paths(parser.root)
        self._collect_semantic_nodes(parser.root, nodes)
        return nodes

    def _assign_paths(self, root: HtmlNode) -> None:
        counters_by_parent: dict[int, dict[str, int]] = {}

        def visit(node: HtmlNode, parent_path: str) -> None:
            if node.parent is None:
                node.path = "document"
            else:
                counters = counters_by_parent.setdefault(id(node.parent), {})
                counters[node.tag] = counters.get(node.tag, 0) + 1
                node.path = f"{parent_path}/{node.tag}[{counters[node.tag]}]"
            for child in node.children:
                visit(child, node.path)

        visit(root, "")

    def _collect_semantic_nodes(self, node: HtmlNode, nodes: list[dict[str, Any]]) -> None:
        if node.tag in SEMANTIC_TAGS:
            public_attrs = {
                key: value
                for key, value in node.attrs.items()
                if key in IMPORTANT_ATTRIBUTES and value
            }
            order = len(nodes)
            text = node.text
            stable_key = self._stable_key(node, text)
            nodes.append({
                "key": stable_key,
                "tag": node.tag,
                "path": node.path,
                "order": order,
                "text": _snippet(text),
                "text_fingerprint": _fingerprint(text),
                "attrs": public_attrs,
            })
        for child in node.children:
            self._collect_semantic_nodes(child, nodes)

    def _stable_key(self, node: HtmlNode, text: str) -> str:
        if node.attrs.get("id"):
            return f"id:{node.attrs['id']}"
        if node.attrs.get("name"):
            return f"name:{node.tag}:{node.attrs['name']}"
        if node.tag == "a" and node.attrs.get("href"):
            return f"a:{node.attrs['href']}"
        if node.tag == "img" and node.attrs.get("src"):
            return f"img:{node.attrs['src']}"
        fingerprint = _fingerprint(text)
        if fingerprint:
            return f"{node.tag}:text:{fingerprint}"
        return f"{node.tag}:path:{node.path}"

    def _unique_by_key(self, nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        seen: dict[str, int] = {}
        keyed: dict[str, dict[str, Any]] = {}
        for node in nodes:
            base_key = str(node["key"])
            seen[base_key] = seen.get(base_key, 0) + 1
            key = base_key if seen[base_key] == 1 else f"{base_key}#{seen[base_key]}"
            keyed[key] = {**node, "match_key": key}
        return keyed

    def _compare_nodes(self, old_nodes: list[dict[str, Any]], new_nodes: list[dict[str, Any]]) -> dict[str, Any]:
        old_by_key = self._unique_by_key(old_nodes)
        new_by_key = self._unique_by_key(new_nodes)
        old_keys = set(old_by_key)
        new_keys = set(new_by_key)

        text_changes: list[dict[str, Any]] = []
        node_changes: list[dict[str, Any]] = []
        attribute_changes: list[dict[str, Any]] = []
        resource_changes: list[dict[str, Any]] = []
        table_changes: list[dict[str, Any]] = []

        for key in sorted(new_keys - old_keys, key=lambda item: new_by_key[item]["order"]):
            node = new_by_key[key]
            node_changes.append(self._node_change("added", None, node))

        for key in sorted(old_keys - new_keys, key=lambda item: old_by_key[item]["order"]):
            node = old_by_key[key]
            node_changes.append(self._node_change("deleted", node, None))

        for key in sorted(old_keys & new_keys, key=lambda item: new_by_key[item]["order"]):
            old = old_by_key[key]
            new = new_by_key[key]

            if old["text_fingerprint"] != new["text_fingerprint"]:
                text_changes.append({
                    "change_type": "modified",
                    "tag": new["tag"],
                    "path": new["path"],
                    "old_text": old["text"],
                    "new_text": new["text"],
                    "similarity": round(difflib.SequenceMatcher(None, old["text"], new["text"]).ratio(), 3),
                })

            if old["order"] != new["order"] and old["text_fingerprint"] == new["text_fingerprint"]:
                node_changes.append(self._node_change("moved", old, new))

            attribute_changes.extend(self._attribute_changes(old, new))
            resource_changes.extend(self._resource_changes(old, new))

            if old["tag"] in {"table", "tr", "td", "th"} and (
                old["text_fingerprint"] != new["text_fingerprint"] or old["attrs"] != new["attrs"]
            ):
                table_changes.append({
                    "change_type": "modified",
                    "tag": new["tag"],
                    "path": new["path"],
                    "old_text": old["text"],
                    "new_text": new["text"],
                })

        stats = {
            "text_added": sum(1 for item in node_changes if item["change_type"] == "added" and item.get("text")),
            "text_deleted": sum(1 for item in node_changes if item["change_type"] == "deleted" and item.get("text")),
            "text_modified": len(text_changes),
            "nodes_added": sum(1 for item in node_changes if item["change_type"] == "added"),
            "nodes_deleted": sum(1 for item in node_changes if item["change_type"] == "deleted"),
            "nodes_moved": sum(1 for item in node_changes if item["change_type"] == "moved"),
            "attributes_changed": len(attribute_changes),
            "resources_changed": len(resource_changes),
            "tables_changed": len(table_changes),
        }
        stats["total_changes"] = sum(stats.values())
        summary = self._summary(stats)
        metadata = {
            "file_type": "html",
            "old_node_count": len(old_nodes),
            "new_node_count": len(new_nodes),
        }
        return {
            "type": "html_diff",
            "text": text_changes,
            "nodes": node_changes,
            "attributes": attribute_changes,
            "resources": resource_changes,
            "tables": table_changes,
            "images": self._image_summary(resource_changes),
            "metadata": metadata,
            "summary": summary,
            "summary_text": summary,
            "stats": stats,
            "changes": {
                "text": text_changes,
                "nodes": node_changes,
                "attributes": attribute_changes,
                "resources": resource_changes,
                "tables": table_changes,
                "images": self._image_summary(resource_changes),
                "metadata": metadata,
                "summary": summary,
                "stats": stats,
            },
        }

    def _node_change(
        self,
        change_type: str,
        old: dict[str, Any] | None,
        new: dict[str, Any] | None,
    ) -> dict[str, Any]:
        node = new or old or {}
        return {
            "change_type": change_type,
            "tag": node.get("tag"),
            "old_path": old.get("path") if old else None,
            "new_path": new.get("path") if new else None,
            "path": node.get("path"),
            "old_text": old.get("text") if old else None,
            "new_text": new.get("text") if new else None,
            "text": node.get("text"),
        }

    def _attribute_changes(self, old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
        changes = []
        old_attrs = old.get("attrs") or {}
        new_attrs = new.get("attrs") or {}
        for attr in sorted(set(old_attrs) | set(new_attrs)):
            if old_attrs.get(attr) == new_attrs.get(attr):
                continue
            changes.append({
                "change_type": "attribute_changed",
                "tag": new["tag"],
                "path": new["path"],
                "attribute": attr,
                "old_value": old_attrs.get(attr),
                "new_value": new_attrs.get(attr),
            })
        return changes

    def _resource_changes(self, old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
        changes = []
        old_attrs = old.get("attrs") or {}
        new_attrs = new.get("attrs") or {}
        for attr in sorted(RESOURCE_ATTRIBUTES):
            if old_attrs.get(attr) == new_attrs.get(attr):
                continue
            if old_attrs.get(attr) is None and new_attrs.get(attr) is None:
                continue
            changes.append({
                "change_type": "resource_changed",
                "tag": new["tag"],
                "path": new["path"],
                "attribute": attr,
                "old_value": old_attrs.get(attr),
                "new_value": new_attrs.get(attr),
            })
        return changes

    def _image_summary(self, resource_changes: list[dict[str, Any]]) -> dict[str, Any]:
        image_changes = [item for item in resource_changes if item.get("tag") == "img"]
        return {
            "added": 0,
            "deleted": 0,
            "replaced": len(image_changes),
            "resized": 0,
            "changes": image_changes,
        }

    def _summary(self, stats: dict[str, int]) -> str:
        parts = []
        if stats["text_modified"]:
            parts.append(f"修改 {stats['text_modified']} 处文本")
        if stats["nodes_added"]:
            parts.append(f"新增 {stats['nodes_added']} 个节点")
        if stats["nodes_deleted"]:
            parts.append(f"删除 {stats['nodes_deleted']} 个节点")
        if stats["nodes_moved"]:
            parts.append(f"移动 {stats['nodes_moved']} 个节点")
        if stats["attributes_changed"]:
            parts.append(f"属性变化 {stats['attributes_changed']} 处")
        if stats["resources_changed"]:
            parts.append(f"资源变化 {stats['resources_changed']} 处")
        if stats["tables_changed"]:
            parts.append(f"表格变化 {stats['tables_changed']} 处")
        return "，".join(parts) if parts else "HTML 内容无变化"
