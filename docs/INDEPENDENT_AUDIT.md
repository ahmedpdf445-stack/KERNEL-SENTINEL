# Code and statistical audit

## Scope and independence

This audit reviews the implementation and mathematical claims in this repository as a separate verification pass from feature construction. It is a repository-level engineering review, not a third-party certification, penetration test, or empirical validation on production telemetry.

## Findings and disposition

The separate read-only review found five actionable issues; all were remediated:

1. **Capacity exhaustion could return success with partial counts.** Capacity now halts ingestion, marks the run incomplete, skips the partial bucket, and makes `detect` return exit code 2. Regression tests cover pipeline state and CLI status.
2. **Out-of-order lifecycle events could mutate PID mappings.** The graph rejects out-of-order additions before graph mutation; the pipeline quarantines them, marks the run incomplete, and skips a still-open affected bucket.
3. **Evidence caps undercounted evaluation true positives.** Display evidence remains capped, while evaluation independently scores every matching feature/event in an alerted minute. A 150-event alerted bucket verifies all events are scored despite the 100-ID evidence cap.
4. **Loss-report `reason` was optional at runtime but required by the JSON Schema.** Runtime parsing now requires it, with a regression test.
5. **Oversized JSON integers could raise an uncaught conversion error.** JSON conversion and recursion failures are wrapped as telemetry validation errors; a 5,000-digit integer test confirms the malformed record is counted and later input is processed.

The final regression suite passed after these changes. This is an independent implementation review within the project workflow, not a third-party certification, penetration test, or real-telemetry/statistical validation.

## Statistical interpretation

The detector reports deviations in synthetic equal-duration count buckets. Its baseline uses a Poisson-inspired variance floor, not a fitted or validated count distribution. Synthetic benchmark metrics are implementation checks only; they do not establish detection efficacy against real threats. False positives during changing-baseline scenarios are meaningful outcomes, not defects to tune away.
