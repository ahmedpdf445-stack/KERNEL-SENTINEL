"""Process graph that models PID reuse with event-backed process generations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from kernel_sentinel.telemetry.schema import Event


class GraphIntegrityError(ValueError):
    """Duplicate event ID, invalid ordering, or graph capacity violation."""


class GraphCapacityError(GraphIntegrityError):
    """The event graph reached its configured hard capacity."""


@dataclass(slots=True)
class ProcessNode:
    identity: str
    process_id: int
    parent_identity: str | None
    process_name: str
    started_at: datetime
    event_ids: list[str] = field(default_factory=list)
    missing_parent: bool = False
    pid_reused: bool = False
    start_observed: bool = False


class ProcessGraph:
    """A bounded in-memory process/event graph; PIDs are not treated as durable IDs."""

    def __init__(self, max_events: int = 100_000) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self.max_events = max_events
        self.events: dict[str, Event] = {}
        self.nodes: dict[str, ProcessNode] = {}
        self.current_by_pid: dict[int, str] = {}
        self.last_by_pid: dict[int, str] = {}
        self.event_identity: dict[str, str] = {}
        self.integrity_issues: list[str] = []
        self.integrity_issue_count = 0
        self._last_timestamp: datetime | None = None

    def record_integrity_issue(self, message: str) -> None:
        self.integrity_issue_count += 1
        if len(self.integrity_issues) < 100:
            self.integrity_issues.append(message)

    def add(self, event: Event) -> ProcessNode:
        if event.event_id in self.events:
            raise GraphIntegrityError(f"duplicate event_id: {event.event_id}")
        if len(self.events) >= self.max_events:
            raise GraphCapacityError(f"event capacity exceeded ({self.max_events})")
        if self._last_timestamp is not None and event.timestamp < self._last_timestamp:
            self.record_integrity_issue(f"out_of_order:{event.event_id}")
            raise GraphIntegrityError(f"out-of-order event quarantined: {event.event_id}")
        self._last_timestamp = max(self._last_timestamp or event.timestamp, event.timestamp)

        identity = self.current_by_pid.get(event.process_id)
        if event.event_type == "process_start":
            prior = self.last_by_pid.get(event.process_id)
            reused = prior is not None and self.nodes[prior].start_observed
            identity = f"{event.process_id}@{event.event_id}"
            parent_identity = self.current_by_pid.get(event.parent_process_id) if event.parent_process_id is not None else None
            missing_parent = event.parent_process_id is not None and parent_identity is None
            if missing_parent:
                self.record_integrity_issue(f"missing_parent:{event.event_id}:{event.parent_process_id}")
            node = ProcessNode(identity, event.process_id, parent_identity, event.process_name,
                               event.timestamp, missing_parent=missing_parent, pid_reused=reused,
                               start_observed=True)
            self.nodes[identity] = node
            self.current_by_pid[event.process_id] = identity
            self.last_by_pid[event.process_id] = identity
            if reused:
                self.record_integrity_issue(f"pid_reused:{event.event_id}:{event.process_id}")
        elif identity is None:
            identity = f"{event.process_id}@implicit-{event.event_id}"
            parent_identity = self.current_by_pid.get(event.parent_process_id) if event.parent_process_id is not None else None
            missing_parent = event.parent_process_id is not None and parent_identity is None
            if missing_parent:
                self.record_integrity_issue(f"missing_parent:{event.event_id}:{event.parent_process_id}")
            self.record_integrity_issue(f"missing_process_start:{event.event_id}:{event.process_id}")
            node = ProcessNode(identity, event.process_id, parent_identity, event.process_name,
                               event.timestamp, missing_parent=missing_parent)
            self.nodes[identity] = node
            self.current_by_pid[event.process_id] = identity
            self.last_by_pid[event.process_id] = identity
        else:
            node = self.nodes[identity]
        node.event_ids.append(event.event_id)
        self.events[event.event_id] = event
        self.event_identity[event.event_id] = identity
        if event.event_type == "process_exit":
            self.current_by_pid.pop(event.process_id, None)
        return node

    def ancestors(self, event_id: str) -> tuple[str, ...]:
        identity = self.event_identity[event_id]
        lineage: list[str] = []
        while identity is not None:
            node = self.nodes[identity]
            lineage.append(identity)
            identity = node.parent_identity
        return tuple(lineage)
