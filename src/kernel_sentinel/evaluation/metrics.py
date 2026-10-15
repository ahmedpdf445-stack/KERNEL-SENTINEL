"""Event-level binary metrics for independent deterministic simulations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from kernel_sentinel.pipeline import EventPipeline
from kernel_sentinel.simulator.generator import simulate
from kernel_sentinel.telemetry.schema import Event, LossReport, serialize_record


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    false_positive_rate: float
    false_negative_rate: float
    detection_delay_seconds: float | None
    positive_events: int
    negative_events: int
    alert_count: int
    malformed_records: int
    dropped_events: int

    def to_dict(self) -> dict[str, int | float | None]:
        return asdict(self)


def evaluate_records(
    records: Iterable[Event | LossReport],
    *,
    window_size: int = 30,
    min_samples: int = 10,
    allowance: float = 0.5,
    threshold: float = 5.0,
) -> EvaluationMetrics:
    rows = tuple(records)
    pipeline = EventPipeline(
        window_size=window_size, min_samples=min_samples,
        allowance=allowance, threshold=threshold,
    )
    result = pipeline.process_lines(serialize_record(row) for row in rows)
    actual = {
        row.event_id: row.scenario_label == "anomaly"
        for row in rows if isinstance(row, Event)
    }
    alerted_features_and_buckets = {(alert.feature, alert.timestamp) for alert in result.alerts}

    def bucket_end(row: Event) -> datetime:
        minute = row.timestamp.astimezone(timezone.utc).replace(second=0, microsecond=0)
        return minute + timedelta(minutes=1)

    predicted = {
        row.event_id
        for row in rows
        if isinstance(row, Event) and (row.event_type, bucket_end(row)) in alerted_features_and_buckets
    }
    tp = sum(actual[event_id] for event_id in predicted)
    fp = len(predicted) - tp
    positives = sum(actual.values())
    negatives = len(actual) - positives
    fn = positives - tp
    tn = negatives - fp
    first_positive = min(
        (row.timestamp for row in rows if isinstance(row, Event) and row.scenario_label == "anomaly"),
        default=None,
    )
    first_detection = min(
        (alert.timestamp for alert in result.alerts
         if any(
             isinstance(row, Event) and actual.get(row.event_id, False)
             and row.event_type == alert.feature and bucket_end(row) == alert.timestamp
             for row in rows
         )),
        default=None,
    )
    delay = (first_detection - first_positive).total_seconds() if first_detection and first_positive else None
    return EvaluationMetrics(
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=tp / (tp + fp) if tp + fp else 0.0,
        recall=tp / positives if positives else 0.0,
        false_positive_rate=fp / negatives if negatives else 0.0,
        false_negative_rate=fn / positives if positives else 0.0,
        detection_delay_seconds=delay,
        positive_events=positives,
        negative_events=negatives,
        alert_count=len(result.alerts),
        malformed_records=result.malformed_records,
        dropped_events=result.dropped_events,
    )


def evaluate_suite(*, seed: int = 4242, buckets: int = 180) -> dict[str, object]:
    """Run fresh seeded datasets per scenario; no tuning to a target score."""
    suite: dict[str, object] = {}
    for offset, scenario in enumerate(("benign", "burst", "suspicious", "changing")):
        dataset = simulate(seed=seed + offset, buckets=buckets, scenario=scenario)
        suite[scenario] = evaluate_records(dataset.records).to_dict()
    return {
        "seed": seed,
        "buckets_per_scenario": buckets,
        "label_policy": "only scenario_label='anomaly' is positive; labels never enter detection",
        "scenarios": suite,
    }
