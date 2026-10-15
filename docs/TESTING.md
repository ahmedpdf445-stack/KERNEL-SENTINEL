# Testing

The suite uses `unittest`, requiring no test framework installation. From the workspace root in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\src"; python -m unittest discover -s tests -v
```

Coverage includes event/loss schema validation and round trips; malformed, duplicate, oversized JSON and extreme integers; duplicate event IDs, out-of-order data, missing parents, PID reuse and ancestry; rolling mean/variance and bounded windows; CUSUM cold start, zero variance, missing observations, and invalid values; pipeline loss, capacity exhaustion, evidence references, malformed inputs, large/empty workloads, and CLI incomplete status; deterministic simulation and label-leakage regression; evaluation metrics, evidence-cap-independent scoring, and reproducibility.

Integration tests exercise simulator records through the JSON serializer, parser, graph, detector, and metrics. CLI commands and generated diagrams are separately smoke-tested during project verification. The final executed count and result are recorded in [ENVIRONMENT_REPORT.md](ENVIRONMENT_REPORT.md); tests are not described as passing unless executed.
