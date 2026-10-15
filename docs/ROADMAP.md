# Roadmap

## Completed MVP scope

- Standard-library event/loss JSONL schema, deterministic seeded generator, malformed/loss injection.
- Single-pass bucketing pipeline, bounded process-generation graph, rolling count baseline, upper CUSUM, evidence-linked alerts.
- Independent seeded scenario evaluation, `unittest`, CLI, local benchmark, generated SVG, and engineering documentation.

## Potential next steps

1. Validate the count model on representative, privacy-reviewed real-world datasets; quantify calibration and threshold sensitivity.
2. Add explicit per-process features and event-order correlation with measurable memory bounds.
3. Add benchmark repetitions, latency distributions, and a documented workload matrix.
4. Design a versioned adapter contract and mock-free integration test plan for a separately scoped Linux collector.
5. Implement and review an actual Linux sensor in a compatible Linux environment, with loss accounting, process-generation identity, permissions review, and end-to-end validation.

No future item is represented as implemented or verified by this MVP.
