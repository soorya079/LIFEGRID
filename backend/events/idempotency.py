"""Local idempotency ledger for event-handler deliveries."""

import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Callable, TypeVar

from backend.services.json_store import JsonFileStore, STORE_LOCK

T = TypeVar("T")
DATA_DIR = Path(os.getenv("LIFEGRID_DATA_DIR", Path(__file__).parents[1] / "data"))
PROCESSED_EVENTS_STORE = JsonFileStore(DATA_DIR / "processed_events.json", [])


class IdempotencyStore:
    """Records successful (event_id, handler) pairs exactly once per local process/store."""

    def __init__(self, store: JsonFileStore | None = None):
        self.store = store or PROCESSED_EVENTS_STORE
        self._lock = RLock()

    def process_once(self, event_id: str, handler: str, operation: Callable[[], T]) -> tuple[T | None, bool]:
        key = f"{event_id}:{handler}"
        with self._lock, STORE_LOCK:
            processed = self.store.read()
            if any(item.get("idempotency_key") == key for item in processed):
                return None, True
            result = operation()
            entry = {
                "idempotency_key": key,
                "event_id": event_id,
                "handler": handler,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            self.store.update(lambda current: ([*current, entry], None))
            return result, False

    def clear(self) -> None:
        self.store.write([])