# Environment and verification report

## Inspected environment

- OS: Windows 11 (`Windows-11-10.0.26200-SP0`, as reported by Python `platform.platform()`).
- Python: CPython 3.14.3, 64-bit.
- Workspace was empty before implementation; no pre-existing project or user changes were present.
- Native Linux/eBPF capability was not available or tested. No claim is made that it was probed beyond the Windows runtime.

## Verified features

Commands executed on this environment include `unittest`, module compilation, standard-library SVG generation, deterministic CLI simulation, CLI detection, loss/malformed-record injection, independent evaluation, and the actual benchmark captured in `reports\`.

## Final test run

`$env:PYTHONPATH = "$PWD\src"; python -m unittest discover -s tests -v` executed **31 tests in 0.840 seconds; all passed** after audit remediation. `python -m compileall -q src tests scripts`, `python -m json.tool schemas\telemetry.schema.json`, and `python -m kernel_sentinel detect .\fixtures\example.jsonl` also completed successfully. Both generated SVGs parsed as XML. The fixture smoke run processed 4 events, with no alerts, errors, or graph issues.

## CLI and artifacts

Smoke run with seed 42 / 120 mixed buckets generated 1,084 events and produced 6 alerts; detection reported 0 malformed records, dropped events, and graph issues. A separate seed 9 run injected 14 dropped events and 16 malformed records; detection reported those counts, marked the result incomplete, reported 14 missing buckets, and exited 2. Evaluation used seed 4242 and 180 buckets per scenario. The exact metric outputs are in `reports\evaluation.json`.

The final seed 2025 / 1,000-bucket benchmark processed 9,117 records in a measured 1.3163 seconds (6,926 records/s; 0.1444 ms mean per record), with a 5,113,699-byte incremental `tracemalloc` peak. It is a single local run, not an RSS measurement or performance guarantee. See `reports\performance.json`.

Evaluation at seed 4242 / 180 buckets per independent scenario observed event-level recall 0.0281 for `burst` and 0.0372 for `suspicious` (with false-negative rates 0.9719 and 0.9628); their first-alert delays were 119 and 55 seconds. The `changing` scenario produced 2 false positives among 1,188 negative events (FPR 0.00168). These are synthetic experiment outcomes, not target scores. Exact metrics and confusion counts are in `reports\evaluation.json`.

## Unverified / future

No Linux environment, native eBPF sensor, live kernel telemetry, other Python version, production workload, paid service, external AI, GPU, or administrator-only capability has been exercised or required.
