"""Runtime configuration file watcher."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Callable

from app.services.event_bus import publish_config_updated
from app.services.runtime_config import apply_runtime_settings
from app.utils.logger import get_logger

logger = get_logger("services.config_watch")


def fingerprint_file(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return "missing"
    stat = file_path.stat()
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return f"{stat.st_mtime_ns}:{stat.st_size}:{digest}"


class ConfigFileWatcher:
    def __init__(
        self,
        env_path_provider: Callable[[], str],
        interval_seconds: float = 1.0,
        debounce_seconds: float = 0.25,
    ) -> None:
        self.env_path_provider = env_path_provider
        self.interval_seconds = interval_seconds
        self.debounce_seconds = debounce_seconds
        self._fingerprint: str | None = None
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._fingerprint = fingerprint_file(self.env_path_provider())
        self._task = asyncio.create_task(self._run(), name="docshop-config-watch")

    async def stop(self) -> None:
        self._stopping.set()
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await asyncio.sleep(self.interval_seconds)
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"Config watcher check failed: {exc}", exc_info=True)

    async def check_once(self) -> bool:
        env_path = self.env_path_provider()
        current = fingerprint_file(env_path)
        if self._fingerprint is None:
            self._fingerprint = current
            return False
        if current == self._fingerprint:
            return False

        if self.debounce_seconds > 0:
            await asyncio.sleep(self.debounce_seconds)
            current = fingerprint_file(env_path)
            if current == self._fingerprint:
                return False

        self._fingerprint = current
        if current == "missing":
            return False

        apply_runtime_settings(env_path)
        await publish_config_updated([], source="env-file")
        return True
