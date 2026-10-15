# Performance and reliability

Run the reproducible local measurement:

```powershell
$env:PYTHONPATH = "$PWD\src"; python -m kernel_sentinel benchmark --seed 2025 --buckets 1000 --output .\reports\performance.json
```

The command records Python version, OS string, seed, requested bucket count, number of JSONL records, processed events, one-run elapsed time, records/second, mean per-record processing time, and `tracemalloc` peak. Simulator objects and serialized input lines are prepared before tracing/timing, so peak bytes measure additional Python allocations during parsing, graphing, and detection—not total process RSS or input storage. The simulator, evaluation helper, and benchmark materialize their generated datasets; their memory therefore grows with requested workload size. `detect` streams input lines, but keeps graph/alert state up to configured capacity. Latency is the total single-run processing time divided by records, not a per-record latency distribution. There is no statistical warm-up, repeated sample, or confidence interval.

The graph accepts at most 100,000 events by default (`detect --max-events` changes this). Per-alert evidence and retained textual diagnostics are capped at 100. The one-pass parser avoids retaining raw lines, but the CLI's benchmark deliberately materializes its test workload; the graph and resulting alerts remain in memory up to graph capacity. This is a local smoke benchmark, not a production capacity claim. Captured values are in [performance.json](../reports/performance.json) and are specific to that environment/run.
