import unittest
from datetime import datetime, timedelta, timezone

from kernel_sentinel.graph.process_graph import GraphIntegrityError, ProcessGraph
from kernel_sentinel.telemetry.schema import Event


def event(event_id, pid, parent=None, offset=0, kind="process_start"):
    return Event(event_id, datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=offset),
                 kind, pid, parent, "p.exe", "simulated")


class ProcessGraphTests(unittest.TestCase):
    def test_parent_relationship_and_ancestor_lineage(self):
        graph = ProcessGraph()
        graph.add(event("root", 1))
        graph.add(event("child", 2, 1, 1))
        graph.add(event("child-op", 2, 1, 2, "file_access"))
        child = graph.nodes["2@child"]
        self.assertEqual(child.parent_identity, "1@root")
        self.assertEqual(graph.ancestors("child-op"), ("2@child", "1@root"))
        self.assertFalse(graph.integrity_issues)

    def test_old_event_keeps_its_original_generation_after_pid_reuse(self):
        graph = ProcessGraph()
        graph.add(event("root", 1))
        graph.add(event("child-first", 2, 1, 1))
        graph.add(event("first-op", 2, 1, 2, "file_access"))
        graph.add(event("child-second", 2, 1, 3))
        self.assertEqual(graph.ancestors("first-op"), ("2@child-first", "1@root"))

    def test_operation_before_observed_start_is_not_misreported_as_pid_reuse(self):
        graph = ProcessGraph()
        graph.add(event("root", 1))
        graph.add(event("early-op", 2, 1, 1, "file_access"))
        graph.add(event("late-start", 2, 1, 2))
        self.assertFalse(any(issue.startswith("pid_reused") for issue in graph.integrity_issues))
        self.assertTrue(any(issue.startswith("missing_process_start") for issue in graph.integrity_issues))

    def test_missing_parent_duplicate_reused_pid_and_out_of_order(self):
        graph = ProcessGraph()
        graph.add(event("orphan", 8, 99, 3))
        with self.assertRaises(GraphIntegrityError):
            graph.add(event("earlier", 9, None, 1))
        graph.add(event("reuse", 8, None, 4))
        with self.assertRaises(GraphIntegrityError):
            graph.add(event("reuse", 8, None, 5))
        self.assertTrue(any(issue.startswith("missing_parent") for issue in graph.integrity_issues))
        self.assertTrue(any(issue.startswith("pid_reused") for issue in graph.integrity_issues))
        self.assertIn("out_of_order:earlier", graph.integrity_issues)
        self.assertNotIn("earlier", graph.events)

    def test_capacity_is_explicit(self):
        graph = ProcessGraph(max_events=1)
        graph.add(event("one", 1))
        with self.assertRaises(GraphIntegrityError):
            graph.add(event("two", 2, offset=1))


if __name__ == "__main__":
    unittest.main()
