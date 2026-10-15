import unittest

from kernel_sentinel.evaluation.metrics import evaluate_records, evaluate_suite


class EvaluationTests(unittest.TestCase):
    def test_empty_dataset_metrics_are_finite_and_defined(self):
        metrics = evaluate_records([])
        self.assertEqual(metrics.true_positives, 0)
        self.assertEqual(metrics.precision, 0)
        self.assertEqual(metrics.recall, 0)
        self.assertEqual(metrics.false_positive_rate, 0)
        self.assertIsNone(metrics.detection_delay_seconds)

    def test_metrics_ranges_suite_scenarios_and_reproducibility(self):
        first = evaluate_suite(seed=55, buckets=50)
        second = evaluate_suite(seed=55, buckets=50)
        self.assertEqual(first, second)
        self.assertEqual(set(first["scenarios"]), {"benign", "burst", "suspicious", "changing"})
        for metrics in first["scenarios"].values():
            for field in ("precision", "recall", "false_positive_rate", "false_negative_rate"):
                self.assertGreaterEqual(metrics[field], 0)
                self.assertLessEqual(metrics[field], 1)
        self.assertGreaterEqual(
            first["scenarios"]["burst"]["detection_delay_seconds"] or 0,
            0,
        )


if __name__ == "__main__":
    unittest.main()
