"""Rolling descriptive statistics and one-sided upper CUSUM."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math


class RollingStats:
    """Bounded rolling population statistics, recomputed stably from the window."""

    def __init__(self, window_size: int = 30, min_samples: int = 10) -> None:
        if window_size < 1 or min_samples < 1 or min_samples > window_size:
            raise ValueError("require 1 <= min_samples <= window_size")
        self.values: deque[float] = deque(maxlen=window_size)
        self.min_samples = min_samples

    @property
    def ready(self) -> bool:
        return len(self.values) >= self.min_samples

    @property
    def mean(self) -> float:
        return math.fsum(self.values) / len(self.values) if self.values else 0.0

    @property
    def variance(self) -> float:
        if not self.values:
            return 0.0
        mean = self.mean
        return math.fsum((value - mean) ** 2 for value in self.values) / len(self.values)

    def observe(self, value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError("observations must be finite and non-negative")
        self.values.append(value)


@dataclass(frozen=True, slots=True)
class CUSUMResult:
    value: float
    baseline_mean: float
    baseline_variance: float
    ready: bool
    alarm: bool


class CUSUM:
    """Upper-sided standardized CUSUM for elevated count observations.

    The baseline is evaluated before the current value is incorporated, preventing
    the observation from masking its own change. Variance is floored at one count
    squared, matching the Poisson variance at a zero estimated rate.
    """

    def __init__(
        self,
        *,
        window_size: int = 30,
        min_samples: int = 10,
        allowance: float = 0.5,
        threshold: float = 5.0,
    ) -> None:
        if allowance < 0 or not math.isfinite(allowance):
            raise ValueError("allowance must be finite and non-negative")
        if threshold <= 0 or not math.isfinite(threshold):
            raise ValueError("threshold must be finite and positive")
        self.stats = RollingStats(window_size, min_samples)
        self.allowance = allowance
        self.threshold = threshold
        self.statistic = 0.0

    def observe(self, value: float, *, missing: bool = False) -> CUSUMResult:
        if missing:
            return CUSUMResult(self.statistic, self.stats.mean, self.stats.variance, self.stats.ready, False)
        ready = self.stats.ready
        mean = self.stats.mean
        variance = max(self.stats.variance, mean, 1.0)
        alarm = False
        if ready:
            residual = (value - mean) / math.sqrt(variance)
            self.statistic = max(0.0, self.statistic + residual - self.allowance)
            alarm = self.statistic >= self.threshold
            score = self.statistic
            if alarm:
                self.statistic = 0.0
        else:
            score = self.statistic
        self.stats.observe(value)
        return CUSUMResult(score, mean, variance, ready, alarm)
