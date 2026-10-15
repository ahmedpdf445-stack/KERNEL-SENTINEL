import json
import unittest
from datetime import datetime, timezone

from kernel_sentinel.telemetry.schema import Event, LossReport, TelemetryValidationError, parse_record, serialize_record


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.event = Event(
            event_id="e-1",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            event_type="process_start",
            process_id=10,
            parent_process_id=None,
            process_name="worker.exe",
            source="simulated",
            scenario_label="benign",
        )

    def test_event_round_trip_and_label_is_evaluation_only(self):
        decoded = parse_record(serialize_record(self.event))
        self.assertEqual(decoded, self.event)
        self.assertEqual(decoded.scenario_label, "benign")
        self.assertEqual(decoded.source, "simulated")

    def test_loss_report_round_trip(self):
        record = LossReport(self.event.timestamp, 2)
        self.assertEqual(parse_record(serialize_record(record)), record)

    def test_invalid_json_and_record_shapes_rejected(self):
        for line in ("{", "[]", '{"timestamp":"2025-01-01T00:00:00Z"}',
                     json.dumps({**self.event.to_dict(), "unexpected": "field"}),
                     '{"record_type":"event","record_type":"event"}'):
            with self.subTest(line=line), self.assertRaises(TelemetryValidationError):
                parse_record(line)

    def test_invalid_timezone_type_id_and_source_rejected(self):
        values = self.event.to_dict()
        values["timestamp"] = "2025-01-01T00:00:00"
        with self.assertRaises(TelemetryValidationError):
            parse_record(json.dumps(values))
        values = self.event.to_dict()
        values["process_id"] = True
        with self.assertRaises(TelemetryValidationError):
            parse_record(json.dumps(values))
        values = self.event.to_dict()
        values["source"] = "live"
        with self.assertRaises(TelemetryValidationError):
            parse_record(json.dumps(values))

    def test_loss_reason_is_required_to_match_json_schema(self):
        values = {
            "record_type": "loss_report",
            "timestamp": "2025-01-01T00:00:00Z",
            "dropped_count": 1,
            "source": "simulated",
        }
        with self.assertRaises(TelemetryValidationError):
            parse_record(json.dumps(values))

    def test_invalid_direct_event_is_rejected(self):
        with self.assertRaises(TelemetryValidationError):
            Event("", self.event.timestamp, "process_start", 1, None, "x", "simulated")

    def test_oversized_record_is_rejected(self):
        with self.assertRaises(TelemetryValidationError):
            parse_record(" " * 65_537)

    def test_repository_fixture_parses(self):
        from pathlib import Path
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "example.jsonl"
        records = [parse_record(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 4)
        self.assertEqual(records[0].event_id, "fixture-root")


if __name__ == "__main__":
    unittest.main()
