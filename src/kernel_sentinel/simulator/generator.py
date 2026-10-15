"""Seeded synthetic workload generator; emits no live operating-system data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random

from kernel_sentinel.telemetry.schema import Event, LossReport


@dataclass(frozen=True, slots=True)
class SimulationResult:
    records: tuple[Event | LossReport, ...]
    generated_event_count: int
    dropped_event_count: int
    malformed_lines: tuple[str, ...]
    seed: int
    scenario: str


def simulate(
    *,
    seed: int = 42,
    buckets: int = 120,
    scenario: str = "mixed",
    loss_rate: float = 0.0,
    malformed_rate: float = 0.0,
) -> SimulationResult:
    """Generate one-minute event-count observations with optional injected faults."""
    if buckets < 1:
        raise ValueError("buckets must be at least 1")
    if scenario not in {"benign", "burst", "suspicious", "changing", "mixed"}:
        raise ValueError("scenario must be benign, burst, suspicious, changing, or mixed")
    for name, rate in (("loss_rate", loss_rate), ("malformed_rate", malformed_rate)):
        if not 0.0 <= rate < 1.0:
            raise ValueError(f"{name} must be in [0, 1)")

    rng = random.Random(seed)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    events: list[Event] = []
    next_pid = 1000
    event_number = 1
    events.append(Event(
        event_id="sim-00000001",
        timestamp=start,
        event_type="process_start",
        process_id=1000,
        parent_process_id=None,
        process_name="sentinel-root.exe",
        source="simulated",
        scenario_label="benign",
    ))
    for bucket in range(buckets):
        stamp = start + timedelta(minutes=bucket)
        selected_scenario = scenario
        if scenario == "mixed":
            if bucket < max(20, buckets // 3):
                selected_scenario = "benign"
            elif bucket < max(40, 2 * buckets // 3):
                selected_scenario = "changing"
            elif bucket % 2:
                selected_scenario = "burst"
            else:
                selected_scenario = "suspicious"
        anomaly = selected_scenario in {"burst", "suspicious"} and bucket >= max(20, buckets // 3)
        shift = selected_scenario == "changing" and bucket >= max(10, buckets // 4)
        label = "anomaly" if anomaly else ("baseline_shift" if shift else "benign")
        type_counts = {
            "process_start": rng.randint(0, 2) + (1 if shift else 0),
            "file_access": rng.randint(1, 4) + (
                rng.randint(8, 14) if selected_scenario == "burst" and anomaly else 0
            ),
            "network_connect": rng.randint(0, 2) + (rng.randint(7, 12) if selected_scenario == "suspicious" and anomaly else 0),
            "process_exec": rng.randint(0, 1) + (1 if shift else 0),
        }
        for event_type, count in type_counts.items():
            for _ in range(count):
                event_number += 1
                if event_type == "process_start":
                    next_pid += 1
                    pid = next_pid
                    parent = 1000
                    event_timestamp = stamp
                else:
                    pid = 1000
                    parent = None
                    event_timestamp = stamp + timedelta(seconds=rng.randrange(1, 60))
                events.append(Event(
                    event_id=f"sim-{event_number:08d}",
                    timestamp=event_timestamp,
                    event_type=event_type,
                    process_id=pid,
                    parent_process_id=parent,
                    process_name="sentinel-worker.exe" if pid > 1000 else "sentinel-root.exe",
                    source="simulated",
                    scenario_label=label,
                ))
    events.sort(key=lambda item: (item.timestamp, item.event_id))
    kept: list[Event | LossReport] = []
    dropped = 0
    malformed: list[str] = []
    loss_by_minute: dict[datetime, int] = {}
    for event in events:
        if rng.random() < loss_rate:
            dropped += 1
            minute = event.timestamp.replace(second=0, microsecond=0)
            loss_by_minute[minute] = loss_by_minute.get(minute, 0) + 1
        else:
            kept.append(event)
        if rng.random() < malformed_rate:
            malformed.append('{"record_type":"event","timestamp":')
    for minute, count in loss_by_minute.items():
        kept.append(LossReport(minute, count, reason="simulated_random_drop"))
    kept.sort(key=lambda item: (item.timestamp, 0 if isinstance(item, LossReport) else 1,
                                item.event_id if isinstance(item, Event) else ""))
    return SimulationResult(tuple(kept), len(events), dropped, tuple(malformed), seed, scenario)
