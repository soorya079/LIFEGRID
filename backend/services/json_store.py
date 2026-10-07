"""Small process-safe-for-threads JSON persistence for local MVP data."""

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Callable

STORE_LOCK = RLock()


class DataStoreError(RuntimeError):
    """A local JSON store could not be read or written safely."""


class JsonFileStore:
    def __init__(self, path: Path, default: Any):
        self.path = Path(path)
        self.default = default

    def _read_unlocked(self) -> Any:
        if not self.path.exists():
            return deepcopy(self.default)
        try:
            text = self.path.read_text(encoding="utf-8")
            if not text.strip():
                return deepcopy(self.default)
            return json.loads(text)
        except (OSError, json.JSONDecodeError) as error:
            raise DataStoreError(f"Could not read local data file: {self.path.name}") from error

    def read(self) -> Any:
        with STORE_LOCK:
            return self._read_unlocked()

    def _write_unlocked(self, value: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                json.dump(value, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
        except OSError as error:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise DataStoreError(f"Could not write local data file: {self.path.name}") from error

    def write(self, value: Any) -> None:
        with STORE_LOCK:
            self._write_unlocked(value)

    def update(self, transform: Callable[[Any], tuple[Any, Any]]) -> Any:
        with STORE_LOCK:
            current = self._read_unlocked()
            updated, result = transform(current)
            self._write_unlocked(updated)
            return result