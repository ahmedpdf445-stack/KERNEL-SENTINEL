import unittest
from dataclasses import replace
import json
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone

from kernel_sentinel.pipeline import EventPipeline, alert_evidence_is_valid
from kernel_sentinel.simulator.generator import simulate
from kernel_sentinel.telemetry.schema import Event, LossReport, serialize_record


def record(event_id, minute, kind="file_access", label="benign", pid=1):
    return Event(event_id, datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minute),
                 kind, pid, None, "worker.exe", "simulated", label)


class PipelineTests(unittest.TestCase):
    def test_alerts_explain_and_link_existing_supporting_evidence(self):
        rows = [record(f"warm-{i}", i, label="benign") for i in range(4)]
        rows += [record(f"high-{i}", 4, label="anomaly") for i in range(10)]
        pipeline = EventPipeline(window_size=4, min_samples=3, allowance=0.1, threshold=2)
        result = pipeline.process_lines(serialize_record(row) for row in rows)
        self.assertTrue(result.alerts)
        alert = result.alerts[0]
        self.assertTrue(alert.evidence_event_ids)
        self.assertTrue(alert_evidence_is_valid(alert, pipeline.graph))
        self.assertIn("not proof", alert.explanation)

    def test_malformed_records_are_counted_and_reported(self):
        result = EventPipeline().process_lines(["not json\n"])
        self.assertEqual(result.malformed_records, 1)
        self.assertEqual(len(result.errors), 1)

    def test_extreme_json_integer_is_counted_and_stream_continues(self):
        extreme = '{"record_type":"event","event_id":"huge","timestamp":"2025-01-01T00:00:00Z","event_type":"process_start","process_id":' + ("9" * 5000) + ',"parent_process_id":null,"process_name":"x","source":"simulated"}'
        result = EventPipeline().process_lines([extreme, serialize_record(record("good", 0, "process_start"))])
        self.assertEqual(result.malformed_records, 1)
        self.assertEqual(result.processed_events, 1)
        self.assertTrue(result.incomplete)

    def test_loss_marks_bucket_missing_and_skips_baseline_observation(self):
        pipeline = EventPipeline(window_size=3, min_samples=2)
        pipeline.ingest(record("a", 0))
        pipeline.ingest(LossReport(datetime(2025, 1, 1, tzinfo=timezone.utc), 3))
        pipeline.ingest(record("b", 1))
        result = pipeline.finish()
        self.assertEqual(result.dropped_events, 3)
        self.assertEqual(result.missing_buckets, 1)
        detector = pipeline.detectors["file_access"]
        self.assertEqual(len(detector.stats.values), 1)

    def test_late_event_is_explicitly_flagged(self):
        pipeline = EventPipeline()
        pipeline.ingest(record("new", 2))
        pipeline.ingest(record("late", 1))
        pipeline.finish()
        self.assertIn("late_event_after_bucket_finalized", pipeline.graph.integrity_issues)
        self.assertNotIn("late", pipeline.graph.events)

    def test_simulation_is_reproducible_and_loss_malformed_are_simulated(self):
        first = simulate(seed=8, buckets=40, loss_rate=0.1, malformed_rate=0.1)
        second = simulate(seed=8, buckets=40, loss_rate=0.1, malformed_rate=0.1)
        self.assertEqual([serialize_record(x) for x in first.records],
                         [serialize_record(x) for x in second.records])
        self.assertEqual(first.malformed_lines, second.malformed_lines)
        self.assertGreater(first.dropped_event_count, 0)
        self.assertTrue(first.malformed_lines)
        self.assertTrue(all(x.source == "simulated" for x in first.records))

    def test_scenario_labels_do_not_change_detector_output(self):
        rows = list(simulate(seed=12, buckets=60, scenario="burst").records)
        changed_labels = [
            replace(row, scenario_label="benign" if row.scenario_label == "anomaly" else "anomaly")
            if isinstance(row, Event) else row
            for row in rows
        ]
        def alerts(records):
            pipeline = EventPipeline(window_size=8, min_samples=5)
            return pipeline.process_lines(serialize_record(row) for row in records).alerts
        self.assertEqual(alerts(rows), alerts(changed_labels))

    def test_evaluation_scores_all_events_when_alert_evidence_is_capped(self):
        from kernel_sentinel.evaluation.metrics import evaluate_records
        rows = [record(f"warm-{minute}", minute) for minute in range(3)]
        rows.extend(record(f"hot-{index}", 3, label="anomaly") for index in range(150))
        serialized = [serialize_record(row) for row in rows]
        pipeline = EventPipeline(window_size=4, min_samples=3, allowance=0.1, threshold=2)
        alerts = pipeline.process_lines(serialized).alerts
        self.assertTrue(any(len(alert.evidence_event_ids) == 100 for alert in alerts))
        metrics = evaluate_records(rows, window_size=4, min_samples=3, allowance=0.1, threshold=2)
        self.assertEqual(metrics.true_positives, 150)
        self.assertEqual(metrics.false_negatives, 0)

    def test_large_batch_and_empty_dataset(self):
        result = EventPipeline(graph_capacity=3000).process_lines(
            serialize_record(row) for row in simulate(seed=2, buckets=300).records
        )
        self.assertGreater(result.processed_events, 1000)
        empty = EventPipeline().process_lines([])
        self.assertEqual(empty.processed_events, 0)
        self.assertEqual(empty.alerts, [])
        self.assertTrue(all(not detector.stats.values for detector in EventPipeline().detectors.values()))

    def test_invalid_detector_configuration_fails_even_for_empty_input(self):
        with self.assertRaises(ValueError):
            EventPipeline(window_size=2, min_samples=3)

    def test_duplicate_and_capacity_failures_mark_stream_incomplete(self):
        duplicate_pipeline = EventPipeline()
        first = record("duplicate", 0, "process_start")
        duplicate_pipeline.ingest(first)
        duplicate_pipeline.ingest(first)
        duplicate_result = duplicate_pipeline.finish()
        self.assertTrue(duplicate_result.incomplete)
        self.assertEqual(duplicate_result.missing_buckets, 1)

        pipeline = EventPipeline(graph_capacity=1)
        pipeline.ingest(record("one", 0, "process_start"))
        pipeline.ingest(record("two", 0, "file_access"))
        result = pipeline.finish()
        self.assertTrue(result.incomplete)
        self.assertEqual(result.termination_reason, "event_capacity_exceeded")
        self.assertEqual(result.processed_events, 1)
        self.assertEqual(result.missing_buckets, 1)

    def test_cli_reports_incomplete_capacity_run_with_nonzero_status(self):
        from kernel_sentinel.cli import command_detect
        with TemporaryDirectory() as folder:
            input_path = Path(folder) / "events.jsonl"
            input_path.write_text(
                "\n".join(serialize_record(row) for row in (
                    record("one", 0, "process_start"),
                    record("two", 0, "file_access"),
                )) + "\n",
                encoding="utf-8",
            )
            args = Namespace(input=str(input_path), window=30, min_samples=10,
                             allowance=0.5, threshold=5.0, max_events=1)
            output = StringIO()
            with redirect_stdout(output):
                status = command_detect(args)
            self.assertEqual(status, 2)
            summary = json.loads(output.getvalue().splitlines()[-1])
            self.assertTrue(summary["incomplete"])
            self.assertEqual(summary["termination_reason"], "event_capacity_exceeded")


if __name__ == "__main__":
    unittest.main()
