"""Command-line entry points for simulation, streaming detection, evaluation, and timing."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import tracemalloc
from typing import TextIO

from kernel_sentinel.evaluation.metrics import evaluate_suite
from kernel_sentinel.pipeline import EventPipeline
from kernel_sentinel.simulator.generator import simulate
from kernel_sentinel.telemetry.schema import serialize_record


def _json_dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def command_simulate(args: argparse.Namespace) -> int:
    dataset = simulate(seed=args.seed, buckets=args.buckets, scenario=args.scenario,
                       loss_rate=args.loss_rate, malformed_rate=args.malformed_rate)
    destination: TextIO
    close = False
    if args.output == "-":
        destination = sys.stdout
    else:
        destination = open(args.output, "w", encoding="utf-8", newline="\n")
        close = True
    try:
        for record in dataset.records:
            destination.write(serialize_record(record) + "\n")
        for line in dataset.malformed_lines:
            destination.write(line + "\n")
    finally:
        if close:
            destination.close()
    print(_json_dump({
        "scenario": dataset.scenario,
        "seed": dataset.seed,
        "generated_events": dataset.generated_event_count,
        "dropped_events": dataset.dropped_event_count,
        "malformed_records_injected": len(dataset.malformed_lines),
        "output": args.output,
        "source": "simulated",
    }), file=sys.stderr)
    return 0


def _alert_dict(alert: object) -> dict[str, object]:
    return {
        "alert_id": alert.alert_id,
        "timestamp": alert.timestamp.isoformat().replace("+00:00", "Z"),
        "feature": alert.feature,
        "observed_count": alert.observed_count,
        "baseline_mean": round(alert.baseline_mean, 6),
        "baseline_variance": round(alert.baseline_variance, 6),
        "cusum_statistic": round(alert.cusum_statistic, 6),
        "evidence_event_ids": list(alert.evidence_event_ids),
        "explanation": alert.explanation,
    }


def command_detect(args: argparse.Namespace) -> int:
    pipeline = EventPipeline(window_size=args.window, min_samples=args.min_samples,
                             allowance=args.allowance, threshold=args.threshold,
                             graph_capacity=args.max_events)
    source: TextIO
    close = False
    if args.input == "-":
        source = sys.stdin
    else:
        source = open(args.input, "r", encoding="utf-8")
        close = True
    try:
        result = pipeline.process_lines(source)
    finally:
        if close:
            source.close()
    for alert in result.alerts:
        print(_json_dump(_alert_dict(alert)))
    print(_json_dump({
        "record_type": "summary",
        "incomplete": result.incomplete,
        "termination_reason": result.termination_reason,
        "processed_events": result.processed_events,
        "alerts": len(result.alerts),
        "malformed_records": result.malformed_records,
        "dropped_events": result.dropped_events,
        "missing_buckets": result.missing_buckets,
        "graph_integrity_issues": pipeline.graph.integrity_issue_count,
        "errors": result.errors,
        "error_count": result.error_count,
    }))
    return 2 if result.incomplete else 0


def command_evaluate(args: argparse.Namespace) -> int:
    result = evaluate_suite(seed=args.seed, buckets=args.buckets)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as output:
            output.write(rendered + "\n")
    print(rendered)
    return 0


def command_benchmark(args: argparse.Namespace) -> int:
    dataset = simulate(seed=args.seed, buckets=args.buckets, scenario="mixed")
    lines = [serialize_record(record) for record in dataset.records]
    pipeline = EventPipeline()
    tracemalloc.start()
    started = time.perf_counter()
    result = pipeline.process_lines(lines)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    records = len(lines)
    benchmark = {
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "seed": args.seed,
        "requested_buckets": args.buckets,
        "input_records": records,
        "processed_events": result.processed_events,
        "elapsed_seconds": elapsed,
        "records_per_second": records / elapsed if elapsed else 0.0,
        "latency_ms_per_record_mean": elapsed * 1000 / records if records else 0.0,
        "tracemalloc_peak_bytes": peak,
        "alerts": len(result.alerts),
        "methodology": "single in-process run; tracemalloc peak during JSONL parsing, graphing and detection",
    }
    rendered = json.dumps(benchmark, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as output:
            output.write(rendered + "\n")
    print(rendered)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kernel-sentinel",
                                     description="Simulated process-behavior anomaly research platform")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sim = subparsers.add_parser("simulate", help="generate deterministic simulated JSONL telemetry")
    sim.add_argument("--seed", type=int, default=42)
    sim.add_argument("--buckets", type=int, default=120)
    sim.add_argument("--scenario", choices=("benign", "burst", "suspicious", "changing", "mixed"), default="mixed")
    sim.add_argument("--loss-rate", type=float, default=0.0)
    sim.add_argument("--malformed-rate", type=float, default=0.0)
    sim.add_argument("--output", default="-", help="output JSONL path or - for stdout")
    sim.set_defaults(handler=command_simulate)

    detect = subparsers.add_parser("detect", help="stream JSONL records through validation and detection")
    detect.add_argument("input", nargs="?", default="-", help="JSONL path or - for stdin")
    detect.add_argument("--window", type=int, default=30)
    detect.add_argument("--min-samples", type=int, default=10)
    detect.add_argument("--allowance", type=float, default=0.5)
    detect.add_argument("--threshold", type=float, default=5.0)
    detect.add_argument("--max-events", type=int, default=100_000)
    detect.set_defaults(handler=command_detect)

    evaluate = subparsers.add_parser("evaluate", help="run deterministic independent evaluation scenarios")
    evaluate.add_argument("--seed", type=int, default=4242)
    evaluate.add_argument("--buckets", type=int, default=180)
    evaluate.add_argument("--output")
    evaluate.set_defaults(handler=command_evaluate)

    benchmark = subparsers.add_parser("benchmark", help="measure local processing throughput and memory")
    benchmark.add_argument("--seed", type=int, default=2025)
    benchmark.add_argument("--buckets", type=int, default=1000)
    benchmark.add_argument("--output")
    benchmark.set_defaults(handler=command_benchmark)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        print(f"kernel-sentinel: {exc}", file=sys.stderr)
        return 2
