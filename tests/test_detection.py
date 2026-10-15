import unittest

from kernel_sentinel.detection.cusum import CUSUM, RollingStats


class DetectionTests(unittest.TestCase):
    def test_rolling_mean_variance_and_bounded_window(self):
        stats = RollingStats(window_size=3, min_samples=2)
        for value in (1, 2, 3, 4):
            stats.observe(value)
        self.assertEqual(list(stats.values), [2, 3, 4])
        self.assertEqual(stats.mean, 3.0)
        self.assertAlmostEqual(stats.variance, 2 / 3)

    def test_cold_start_and_zero_variance_boundary(self):
        detector = CUSUM(window_size=3, min_samples=3, threshold=2, allowance=0.5)
        self.assertFalse(detector.observe(0).ready)
        self.assertFalse(detector.observe(0).ready)
        self.assertFalse(detector.observe(0).ready)
        result = detector.observe(10)
        self.assertTrue(result.ready)
        self.assertTrue(result.alarm)
        self.assertEqual(result.baseline_variance, 1.0)

    def test_missing_observation_freezes_state_and_sample_count(self):
        detector = CUSUM(window_size=4, min_samples=2, threshold=3)
        detector.observe(2)
        before = list(detector.stats.values)
        state = detector.statistic
        result = detector.observe(100, missing=True)
        self.assertFalse(result.alarm)
        self.assertEqual(list(detector.stats.values), before)
        self.assertEqual(detector.statistic, state)

    def test_invalid_parameters_and_observations(self):
        with self.assertRaises(ValueError):
            RollingStats(2, 3)
        detector = CUSUM()
        for invalid in (-1, float("nan"), float("inf")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                detector.observe(invalid)


if __name__ == "__main__":
    unittest.main()
