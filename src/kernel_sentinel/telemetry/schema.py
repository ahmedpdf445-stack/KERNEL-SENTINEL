"""Strict, dependency-free telemetry record validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

EVENT_TYPES = frozenset({"process_start", "process_exec", "file_access", "network_connect", "process_exit"})
SIMULATED_SOURCE = "simulated"
MAX_RECORD_CHARS = 65_536


class TelemetryValidationError(ValueError):
    """Raised when a telemetry record is malformed or violates the schema."""


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TelemetryValidationError("timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryValidationError("timestamp must be valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TelemetryValidationError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    timestamp: datetime
    event_type: str
    process_id: int
    parent_process_id: int | None
    process_name: str
    source: str
    scenario_label: str | None = None
    record_type: str = "event"

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id or len(self.event_id) > 256:
            raise TelemetryValidationError("event_id must be a non-empty string of at most 256 characters")
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise TelemetryValidationError("timestamp must include a timezone")
        if not isinstance(self.event_type, str) or self.event_type not in EVENT_TYPES:
            raise TelemetryValidationError(f"unsupported event_type: {self.event_type!r}")
        if isinstance(self.process_id, bool) or not isinstance(self.process_id, int) or self.process_id < 0:
            raise TelemetryValidationError("process_id must be a non-negative integer")
        if self.parent_process_id is not None and (
            isinstance(self.parent_process_id, bool)
            or not isinstance(self.parent_process_id, int)
            or self.parent_process_id < 0
        ):
            raise TelemetryValidationError("parent_process_id must be null or a non-negative integer")
        if not isinstance(self.process_name, str) or not self.process_name or len(self.process_name) > 256:
            raise TelemetryValidationError("process_name must be a non-empty string of at most 256 characters")
        if self.source != SIMULATED_SOURCE:
            raise TelemetryValidationError("only source='simulated' is supported by this MVP")
        if self.scenario_label is not None and (
            not isinstance(self.scenario_label, str) or len(self.scenario_label) > 128
        ):
            raise TelemetryValidationError("scenario_label must be at most 128 characters or null")
        if self.record_type != "event":
            raise TelemetryValidationError("event record_type must be 'event'")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "event",
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
            "event_type": self.event_type,
            "process_id": self.process_id,
            "parent_process_id": self.parent_process_id,
            "process_name": self.process_name,
            "source": self.source,
            "scenario_label": self.scenario_label,
        }


@dataclass(frozen=True, slots=True)
class LossReport:
    timestamp: datetime
    dropped_count: int
    source: str = SIMULATED_SOURCE
    reason: str = "simulated_event_loss"
    record_type: str = "loss_report"

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise TelemetryValidationError("loss timestamp must include a timezone")
        if isinstance(self.dropped_count, bool) or not isinstance(self.dropped_count, int) or self.dropped_count <= 0:
            raise TelemetryValidationError("dropped_count must be a positive integer")
        if self.source != SIMULATED_SOURCE:
            raise TelemetryValidationError("only source='simulated' is supported by this MVP")
        if not isinstance(self.reason, str) or not self.reason or len(self.reason) > 256:
            raise TelemetryValidationError("loss reason must be non-empty and at most 256 characters")
        if self.record_type != "loss_report":
            raise TelemetryValidationError("loss record_type must be 'loss_report'")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "loss_report",
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
            "dropped_count": self.dropped_count,
            "source": self.source,
            "reason": self.reason,
        }


def parse_record(line: str) -> Event | LossReport:
    """Parse and validate exactly one JSON Lines record."""
    if not isinstance(line, str):
        raise TelemetryValidationError("record must be supplied as text")
    if len(line) > MAX_RECORD_CHARS:
        raise TelemetryValidationError(f"record exceeds the {MAX_RECORD_CHARS}-character limit")
    try:
        value = json.loads(line, object_pairs_hook=_unique_object)
    except (ValueError, TypeError, RecursionError) as exc:
        raise TelemetryValidationError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TelemetryValidationError("record must be a JSON object")
    record_type = value.get("record_type")
    try:
        timestamp = _timestamp(value.get("timestamp"))
        if record_type == "event":
            required = {
                "event_id", "timestamp", "event_type", "process_id",
                "parent_process_id", "process_name", "source",
            }
            allowed = required | {"record_type", "scenario_label"}
            extra = value.keys() - allowed
            if extra:
                raise TelemetryValidationError(f"unknown fields: {', '.join(sorted(extra))}")
            missing = required.difference(value)
            if missing:
                raise TelemetryValidationError(f"missing required fields: {', '.join(sorted(missing))}")
            return Event(
                event_id=value["event_id"],
                timestamp=timestamp,
                event_type=value["event_type"],
                process_id=value["process_id"],
                parent_process_id=value["parent_process_id"],
                process_name=value["process_name"],
                source=value["source"],
                scenario_label=value.get("scenario_label"),
            )
        if record_type == "loss_report":
            allowed = {"record_type", "timestamp", "dropped_count", "source", "reason"}
            extra = value.keys() - allowed
            if extra:
                raise TelemetryValidationError(f"unknown fields: {', '.join(sorted(extra))}")
            return LossReport(
                timestamp=timestamp,
                dropped_count=value.get("dropped_count"),
                source=value.get("source"),
                reason=value.get("reason"),
            )
    except (KeyError, TypeError) as exc:
        raise TelemetryValidationError(f"invalid {record_type!r} record: {exc}") from exc
    raise TelemetryValidationError(f"unsupported record_type: {record_type!r}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise TelemetryValidationError(f"duplicate JSON field: {key}")
        value[key] = item
    return value


def serialize_record(record: Event | LossReport) -> str:
    return json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
