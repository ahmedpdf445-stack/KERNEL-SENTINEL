# Limitations

- Every current record is synthetic and explicitly tagged `"simulated"`; no host process is observed.
- Simple one-minute event-type counts lose ordering and context within a bucket. No process-specific feature model, seasonality, correlation correction, calibrated significance test, or threshold-learning system is implemented.
- The Poisson motivation is approximate; real process behavior is often bursty and overdispersed. Alerts indicate statistical deviation, not maliciousness.
- A loss report conservatively skips all features in one minute, without estimating how the missing events would have changed counts. Malformed lines have no timestamp and cannot be assigned to a missing bucket.
- A completely silent interval with neither events nor a loss/watermark record cannot be distinguished from a valid quiet interval. The simulator, evaluation, and benchmark materialize their generated dataset; large requested bucket counts grow memory linearly.
- The in-memory graph is capped, lacks persistence, and has only simulated process identity; PID namespaces, boot IDs, and kernel process cookies are absent.
- Evaluation labels and scenarios are synthetic and intentionally simple. The data does not represent real adversaries, normal users, or operational base rates. Scores are not evidence of field accuracy.
- Performance numbers are single-run measurements on one Windows machine; traced allocations are incremental, not RSS.
- Investigation agent support is a protocol only; no model, prompts, API, or automatic action exists.
- Linux/eBPF collector, kernel compatibility, permissions, verifier behavior, and integration remain future work and unverified.
