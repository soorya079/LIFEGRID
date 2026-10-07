"""Local and Amazon EventBridge implementations behind a common publisher."""

import json
import logging
import os
from collections import defaultdict
from datetime import timezone
from pathlib import Path
from threading import RLock
from typing import Callable, Protocol

from backend.events.event_models import (
    DomainEvent,
    EventType,
    FailedEventRecord,
    HandlerResult,
    PublishResult,
)
from backend.events.idempotency import IdempotencyStore
from backend.services.json_store import JsonFileStore, STORE_LOCK

LOGGER = logging.getLogger(__name__)
DATA_DIR = Path(os.getenv("LIFEGRID_DATA_DIR", Path(__file__).parents[1] / "data"))
EVENTS_STORE = JsonFileStore(DATA_DIR / "events.json", [])
FAILED_EVENTS_STORE = JsonFileStore(DATA_DIR / "failed_events.json", [])

EventHandler = Callable[[DomainEvent, "EventBus"], dict | None]


class EventBus(Protocol):
    mode: str

    def publish(self, event: DomainEvent) -> PublishResult: ...


class LocalEventBus:
    mode = "local"

    def __init__(
        self,
        events_store: JsonFileStore | None = None,
        failed_store: JsonFileStore | None = None,
        idempotency: IdempotencyStore | None = None,
        max_attempts: int = 2,
    ):
        self.events_store = events_store or EVENTS_STORE
        self.failed_store = failed_store or FAILED_EVENTS_STORE
        self.idempotency = idempotency or IdempotencyStore()
        self.max_attempts = max(1, max_attempts)
        self._handlers: dict[EventType, list[tuple[str, EventHandler]]] = defaultdict(list)
        self._publish_lock = RLock()

    def subscribe(self, event_type: EventType, name: str, handler: EventHandler) -> None:
        self._handlers[event_type].append((name, handler))

    def _persist_event(self, event: DomainEvent) -> None:
        encoded = event.model_dump(mode="json")

        def append(current: list[dict]) -> tuple[list[dict], None]:
            if any(item.get("event_id") == event.event_id for item in current):
                return current, None
            return [*current, encoded], None

        self.events_store.update(append)

    def _record_failure(self, event: DomainEvent, handler: str, attempt: int, error: Exception) -> None:
        record = FailedEventRecord(
            event_id=event.event_id,
            event_type=event.event_type,
            handler=handler,
            report_id=event.report_id,
            error=f"{type(error).__name__}: {error}",
            attempt=attempt,
        ).model_dump(mode="json")
        self.failed_store.update(lambda current: ([*current, record], None))

    def publish(self, event: DomainEvent) -> PublishResult:
        with self._publish_lock:
            self._persist_event(event)
            outcomes: list[HandlerResult] = []
            for handler_name, handler in self._handlers.get(event.event_type, []):
                def execute() -> dict | None:
                    return handler(event, self)

                try:
                    _, already_processed = self.idempotency.process_once(
                        event.event_id, handler_name, execute
                    )
                    outcomes.append(HandlerResult(
                        event_id=event.event_id,
                        handler=handler_name,
                        already_processed=already_processed,
                        success=True,
                        attempts=0 if already_processed else 1,
                    ))
                except Exception as first_error:
                    error = first_error
                    succeeded = False
                    attempts = 1
                    self._record_failure(event, handler_name, attempts, error)
                    while attempts < self.max_attempts and not succeeded:
                        attempts += 1
                        try:
                            self.idempotency.process_once(event.event_id, handler_name, execute)
                            succeeded = True
                        except Exception as retry_error:
                            error = retry_error
                            self._record_failure(event, handler_name, attempts, error)
                    LOGGER.error(
                        "LIFEGRID event handler outcome",
                        extra={"event_id": event.event_id, "handler": handler_name,
                               "report_id": event.report_id, "attempts": attempts,
                               "success": succeeded},
                    )
                    outcomes.append(HandlerResult(
                        event_id=event.event_id,
                        handler=handler_name,
                        already_processed=False,
                        success=succeeded,
                        attempts=attempts,
                        error=None if succeeded else f"{type(error).__name__}: {error}",
                    ))
            accepted = all(item.success for item in outcomes)
            return PublishResult(event=event, accepted=accepted, mode=self.mode, handlers=outcomes)


class EventBridgeEventBus:
    mode = "aws"

    def __init__(self, bus_name: str | None = None, client=None):
        self.bus_name = bus_name or os.getenv("EVENT_BUS_NAME", "LIFEGRID-EventBus")
        self._client = client

    @property
    def client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("events", region_name=os.getenv("AWS_REGION", "ap-south-1"))
        return self._client

    def publish(self, event: DomainEvent) -> PublishResult:
        response = self.client.put_events(Entries=[{
            "EventBusName": self.bus_name,
            "Source": event.source,
            "DetailType": event.event_type.value,
            "Time": event.timestamp.astimezone(timezone.utc),
            "Detail": json.dumps(event.model_dump(mode="json"), separators=(",", ":")),
        }])
        entries = response.get("Entries", [])
        error = entries[0].get("ErrorCode") if entries else "EMPTY_RESPONSE"
        if response.get("FailedEntryCount", 0) or error:
            raise RuntimeError(f"EventBridge rejected event: {error or 'unknown failure'}")
        return PublishResult(event=event, accepted=True, mode=self.mode, handlers=[])


_BUS: EventBus | None = None
_BUS_LOCK = RLock()


def get_event_bus() -> EventBus:
    global _BUS
    with _BUS_LOCK:
        if _BUS is None:
            if os.getenv("APP_ENV", "local").lower() == "aws":
                _BUS = EventBridgeEventBus()
            else:
                local_bus = LocalEventBus()
                from backend.events.handlers import register_default_handlers
                register_default_handlers(local_bus)
                _BUS = local_bus
        return _BUS


def set_event_bus_for_tests(bus: EventBus | None) -> None:
    global _BUS
    with _BUS_LOCK:
        _BUS = bus


def local_event_history() -> list[dict]:
    return EVENTS_STORE.read()


def local_failed_event_history() -> list[dict]:
    return FAILED_EVENTS_STORE.read()