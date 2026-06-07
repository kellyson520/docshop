from abc import ABC, abstractmethod


class BaseDiffEngine(ABC):
    """Base class for document diff engines."""

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
