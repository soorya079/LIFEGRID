"""
DynamoDB-backed stores for LIFEGRID Lambda functions.

These replace the local JsonFileStore when APP_ENV=aws.
Each store wraps a single DynamoDB table with simple get/put/scan operations
using the existing domain models unchanged.
"""

from __future__ import annotations

import decimal
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger(__name__)
REGION = os.environ.get("AWS_REGION_NAME", "ap-south-1")

_dynamodb = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return _dynamodb


def _float_to_decimal(obj):
    if isinstance(obj, float):
        return decimal.Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_float_to_decimal(v) for v in obj]
    return obj


def _decimal_to_float(obj):
    if isinstance(obj, decimal.Decimal):
        # Optional: return int if it's a whole number, but float is safer
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(v) for v in obj]
    return obj


class DynamoDBStore:
    """Thin DynamoDB wrapper matching the read/write contract of JsonFileStore."""

    def __init__(self, table_name: str, partition_key: str, default: Any = None):
        self.table_name = table_name
        self.partition_key = partition_key
        self.default = default if default is not None else []
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = _get_dynamodb().Table(self.table_name)
        return self._table

    def read(self) -> list[dict]:
        """Scan and return all items as a list of dicts."""
        try:
            response = self.table.scan()
            items = response.get("Items", [])
            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))
            return _decimal_to_float(items)
        except ClientError as e:
            LOGGER.error("DynamoDB scan failed", extra={"table": self.table_name, "error": str(e)})
            return list(self.default)

    def get_item(self, key_value: str) -> dict | None:
        """Get a single item by partition key."""
        try:
            response = self.table.get_item(Key={self.partition_key: key_value})
            item = response.get("Item")
            if item:
                return _decimal_to_float(item)
            return None
        except ClientError as e:
            LOGGER.error("DynamoDB get_item failed", extra={"table": self.table_name, "key": key_value, "error": str(e)})
            return None

    def put_item(self, item: dict) -> None:
        """Put/overwrite a single item."""
        try:
            dynamo_item = _float_to_decimal(item)
            self.table.put_item(Item=dynamo_item)
        except ClientError as e:
            LOGGER.error("DynamoDB put_item failed", extra={"table": self.table_name, "error": str(e)})
            raise

    def delete_item(self, key_value: str) -> None:
        """Delete a single item by partition key."""
        try:
            self.table.delete_item(Key={self.partition_key: key_value})
        except ClientError as e:
            LOGGER.error("DynamoDB delete_item failed", extra={"table": self.table_name, "error": str(e)})
            raise

    def update(self, updater):
        import copy
        current = self.read()
        current_copy = copy.deepcopy(current)
        new_list, result = updater(current_copy)
        
        # Write only changed/new items back
        current_keys = {item.get(self.partition_key) for item in current}
        new_keys = {item.get(self.partition_key) for item in new_list}
        
        # Delete removed items
        for removed_key in current_keys - new_keys:
            if removed_key:
                self.delete_item(removed_key)
                
        # Put new/updated items
        for item in new_list:
            item_key = item.get(self.partition_key)
            current_item = next((i for i in current if i.get(self.partition_key) == item_key), None)
            if current_item != item:
                self.put_item(item)
        return result

    def write(self, items: list[dict]) -> None:
        """Overwrite the collection completely."""
        for item in items:
            self.put_item(item)


class DynamoDBIdempotencyStore:
    """DynamoDB-backed idempotency ledger for Lambda event handlers."""

    def __init__(self, table_name: str, ttl_seconds: int = 86400 * 7):
        self.table_name = table_name
        self.ttl_seconds = ttl_seconds
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = _get_dynamodb().Table(self.table_name)
        return self._table

    def is_processed(self, event_id: str, handler: str) -> bool:
        key = f"{event_id}:{handler}"
        try:
            response = self.table.get_item(Key={"idempotency_key": key})
            return "Item" in response
        except ClientError:
            return False

    def mark_processed(self, event_id: str, handler: str) -> None:
        key = f"{event_id}:{handler}"
        ttl = int(time.time()) + self.ttl_seconds
        try:
            self.table.put_item(Item={
                "idempotency_key": key,
                "event_id": event_id,
                "handler": handler,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "ttl": ttl,
            })
        except ClientError as e:
            LOGGER.warning("Could not mark event as processed", extra={"key": key, "error": str(e)})

    def process_once(self, event_id: str, handler: str, operation) -> tuple[Any, bool]:
        """Idempotent execution — runs operation only if not already processed."""
        if self.is_processed(event_id, handler):
            return None, True
        result = operation()
        self.mark_processed(event_id, handler)
        return result, False
