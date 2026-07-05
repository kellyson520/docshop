from abc import ABC, abstractmethod
from typing import Any


class BaseDiffEngine(ABC):
    """Base class for document diff engines."""

    # 防止 diff 结果在入库/返回前无限膨胀。阈值足够大，不影响正常文档，
    # 只在异常大量明细或超长字符串时裁剪并保留摘要标记。
    max_diff_list_items = 5000
    max_diff_string_chars = 20000

    def _cap_diff_payload(
        self,
        payload: Any,
        *,
        max_list_items: int | None = None,
        max_string_chars: int | None = None,
    ) -> Any:
        """Return a JSON-safe diff payload with bounded lists and strings."""
        list_limit = self.max_diff_list_items if max_list_items is None else max_list_items
        string_limit = self.max_diff_string_chars if max_string_chars is None else max_string_chars
        truncated = False

        def cap(value: Any) -> Any:
            nonlocal truncated

            if isinstance(value, str):
                if string_limit >= 0 and len(value) > string_limit:
                    truncated = True
                    return f"{value[:string_limit]}... [truncated]"
                return value

            if isinstance(value, list):
                if list_limit >= 0 and len(value) > list_limit:
                    truncated = True
                    return [
                        *(cap(item) for item in value[:list_limit]),
                        {"_truncated": True, "omitted_items": len(value) - list_limit},
                    ]
                return [cap(item) for item in value]

            if isinstance(value, tuple):
                return tuple(cap(item) for item in value)

            if isinstance(value, dict):
                return {key: cap(item) for key, item in value.items()}

            return value

        capped = cap(payload)
        if truncated and isinstance(capped, dict):
            metadata = capped.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["payload_truncated"] = True
                metadata["payload_limits"] = {
                    "max_list_items": list_limit,
                    "max_string_chars": string_limit,
                }

                changes = capped.get("changes")
                if isinstance(changes, dict):
                    changes["metadata"] = metadata

        return capped

    @abstractmethod
    def compare(self, old_path: str, new_path: str) -> dict:
        """
        Compare two versions of a document.
        Returns a dict with diff results.
        """
        pass

    @abstractmethod
    def generate_summary(self, diff_data: dict) -> str:
        """
        Generate a human-readable summary of the diff.
        """
        pass
