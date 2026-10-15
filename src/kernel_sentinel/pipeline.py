"""Single-pass ingestion, bucketing, process correlation, and alert production."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from kernel_sentinel.detection.cusum import CUSUM
from kernel_sentinel.graph.process_graph import GraphCapacityError, GraphIntegrityError, ProcessGraph
from kernel_sentinel.telemetry.schema import (
    EVENT_TYPES, Event, LossReport, TelemetryValidationError, parse_record,
)


@dataclass(frozen=True, slots=True)
class Alert:
    alert_id: str
    timestamp: datetime
    feature: str
    observed_count: int
    baseline_mean: float
    baseline_variance: float
    cusum_statistic: float
    evidence_event_ids: tuple[str, ...]
    explanation: str


@dataclass(slots=True)
class PipelineResult:
    alerts: list[Alert] = field(default_factory=list)
    malformed_records: int = 0
    dropped_events: int = 0
    missing_buckets: int = 0
    processed_events: int = 0
    errors: list[str] = field(default_factory=list)
    error_count: int = 0
    incomplete: bool = False
    termination_reason: str | None = None


class EventPipeline:
    """Accept one-minute event counts; loss marks its bucket missing for every feature."""

    def __init__(
        self,
        *,
        window_size: int = 30,
        min_samples: int = 10,
        allowance: float = 0.5,
        threshold: float = 5.0,
        graph_capacity: int = 100_000,
        max_evidence_per_alert: int = 100,
    ) -> None:
        if max_evidence_per_alert < 1:
            raise ValueError("max_evidence_per_alert must be positive")
        self.detectors: dict[str, CUSUM] = {
            feature: CUSUM(
                window_size=window_size, min_samples=min_samples,
                allowance=allowance, threshold=threshold,
            )
            for feature in EVENT_TYPES
        }
        self.graph = ProcessGraph(graph_capacity)
        self.max_evidence_per_alert = max_evidence_per_alert
        self.result = PipelineResult()
        self._bucket: datetime | None = None
        self._counts: dict[str, int] = {}
        self._evidence: dict[str, list[str]] = {}
        self._bucket_missing = False
        self._last_input_timestamp: datetime | None = None
        self._alert_number = 0
        self._halted = False

    def _error(self, message: str) -> None:
        self.result.error_count += 1
        if len(self.result.errors) < 100:
            self.result.errors.append(message[:512])

    @staticmethod
    def _minute(timestamp: datetime) -> datetime:
        stamp = timestamp.astimezone(timezone.utc)
        return stamp.replace(second=0, microsecond=0)

    def ingest_line(self, line: str) -> None:
        if self._halted:
            return
        try:
            record = parse_record(line)
        except TelemetryValidationError as exc:
            self.result.malformed_records += 1
            self.result.incomplete = True
            self._error(str(exc))
            return
        self.ingest(record)

    def ingest(self, record: Event | LossReport) -> None:
        minute = self._minute(record.timestamp)
        if self._last_input_timestamp is not None and record.timestamp < self._last_input_timestamp:
            self.graph.record_integrity_issue("out_of_order_input")
            self.result.incomplete = True
            self._error("out_of_order_input; event quarantined")
            if self._bucket == minute:
                self._bucket_missing = True
            elif self._bucket is not None and minute < self._bucket:
                self.graph.record_integrity_issue("late_event_after_bucket_finalized")
            return
        self._last_input_timestamp = record.timestamp
        if self._bucket is not None and minute < self._bucket:
            self.graph.record_integrity_issue("late_event_after_bucket_finalized")
            self.result.incomplete = True
            self._error("late_event_after_bucket_finalized")
            return
        if self._bucket is not None and minute > self._bucket:
            self._finalize_bucket()
        if self._bucket != minute:
            self._bucket = minute
            self._counts = {}
            self._evidence = {}
            self._bucket_missing = False
        if isinstance(record, LossReport):
            self.result.dropped_events += record.dropped_count
            self.result.incomplete = True
            self._bucket_missing = True
            return
        try:
            node = self.graph.add(record)
        except GraphCapacityError as exc:
            self.result.incomplete = True
            self.result.termination_reason = "event_capacity_exceeded"
            self._bucket_missing = True
            self._error(str(exc))
            self._halted = True
            return
        except GraphIntegrityError as exc:
            self.result.incomplete = True
            if self._bucket == minute:
                self._bucket_missing = True
            self._error(str(exc))
            return
        if node.missing_parent or (
            not node.start_observed and record.event_type != "process_start"
        ):
            self.result.incomplete = True
        if node.missing_parent and record.event_type == "process_start":
            self.graph.record_integrity_issue(f"orphan_start:{record.event_id}")
        self.result.processed_events += 1
        self._counts[record.event_type] = self._counts.get(record.event_type, 0) + 1
        evidence = self._evidence.setdefault(record.event_type, [])
        if len(evidence) < self.max_evidence_per_alert:
            evidence.append(record.event_id)

    def _detector(self, feature: str) -> CUSUM:
        return self.detectors[feature]

    def _finalize_bucket(self) -> None:
        if self._bucket is None:
            return
        if self._bucket_missing:
            self.result.missing_buckets += 1
            for detector in self.detectors.values():
                detector.observe(0, missing=True)
            self._bucket = None
            return
        features = set(self.detectors) | set(self._counts)
        for feature in sorted(features):
            detector = self._detector(feature)
            count = self._counts.get(feature, 0)
            result = detector.observe(count)
            if result.alarm:
                ids = tuple(self._evidence.get(feature, ())[:self.max_evidence_per_alert])
                self._alert_number += 1
                self.result.alerts.append(Alert(
                    alert_id=f"alert-{self._alert_number:06d}",
                    timestamp=self._bucket + timedelta(minutes=1),
                    feature=feature,
                    observed_count=count,
                    baseline_mean=result.baseline_mean,
                    baseline_variance=result.baseline_variance,
                    cusum_statistic=result.value,
                    evidence_event_ids=ids,
                    explanation=(
                        f"{feature} count {count} exceeded its rolling baseline "
                        f"(mean={result.baseline_mean:.3f}, variance={result.baseline_variance:.3f}); "
                        "CUSUM threshold crossed. Statistical deviation is not proof of malicious intent."
                    ),
                ))
        self._bucket = None

    def finish(self) -> PipelineResult:
        self._finalize_bucket()
        return self.result

    def process_lines(self, lines: Iterable[str]) -> PipelineResult:
        for line in lines:
            if self._halted:
                break
            self.ingest_line(line)
        return self.finish()


def alert_evidence_is_valid(alert: Alert, graph: ProcessGraph) -> bool:
    return bool(alert.evidence_event_ids) and all(event_id in graph.events for event_id in alert.evidence_event_ids)
