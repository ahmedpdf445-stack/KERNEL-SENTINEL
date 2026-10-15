# Mathematical model

## Observation and baseline

For each event type \(j\), the observation \(X_{j,t}\) is the count in a finalized UTC one-minute interval. Each detector maintains at most \(W\) prior, non-missing counts. The rolling descriptive mean and population variance are

\[
\bar{x}_t = \frac{1}{n}\sum_{i=1}^{n} x_i,\qquad
s_t^2 = \frac{1}{n}\sum_{i=1}^{n}(x_i-\bar{x}_t)^2 .
\]

These are recomputed with `math.fsum` over the bounded window, avoiding a subtractive rolling-sum variance formula. Cold start is explicit: no alarms are evaluated until `min_samples` prior observations exist. The current count is tested against the prior baseline and only then added to it.

## Count model and zero variance

For independent counts over equal-duration exposure, \(X_t\sim\mathrm{Poisson}(\lambda)\) is a useful baseline approximation, with \(E[X]=Var[X]=\lambda\). Real process events are often overdispersed, correlated, and non-stationary, so the approximation is not asserted as a universal model. The standard deviation uses

\[
\sigma_t = \sqrt{\max(s_t^2,\bar{x}_t,1)} .
\]

The floor of one count squared provides defined scaling for all-zero startup and constant baselines; it is a practical regularizer, not a learned uncertainty estimate.

## Upper CUSUM

For standardized residual \(z_t=(X_t-\bar{x}_t)/\sigma_t\), the positive one-sided statistic is

\[
S_t=\max(0,S_{t-1}+z_t-k),
\]

with non-negative allowance \(k\). An alarm occurs when \(S_t\ge h\); the statistic then resets to zero. The alert preserves the threshold-crossing score and baseline parameters. This detects sustained upward shifts; a separate lower-sided detector would be needed for decreases. Defaults are \(W=30\), `min_samples=10`, \(k=0.5\), and \(h=5.0`, all configurable on the CLI.

## Missing observations and bucket finalization

A loss report makes the corresponding bucket unknown, not zero. CUSUM and rolling statistics are frozen for that minute; dropped count is separately accumulated. Buckets are finalized as soon as the stream reaches the next minute or at EOF. The reported alert timestamp is the end of its observation minute, representing the earliest bucket-boundary decision time; actual transport delay is not modeled.

## Interpretation and evaluation

Alerts provide event type, observed count, prior mean/variance, threshold-crossing statistic, and up to 100 supporting event IDs. For event-level scoring, an event is predicted positive when its event type matches an alerted feature in that event's bucket; metric scoring is not truncated by the alert's display-evidence cap. Only `scenario_label == "anomaly"` is a positive ground truth; `"baseline_shift"` intentionally remains negative to expose drift-induced false positives. Precision, recall, FPR, and FNR use event-level confusion counts; delay compares the first detected anomalous bucket boundary with the earliest positive event timestamp. An absent detection has null delay. These synthetic estimates do not establish real-world detection quality.
