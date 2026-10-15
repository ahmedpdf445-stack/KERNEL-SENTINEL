# Project overview

Kernel Sentinel is a research harness for process event analytics, implemented in Python with no core third-party dependencies. It provides deterministic event generation, a JSON Lines contract, single-pass parsing, a process-generation graph, rolling count statistics, a one-sided CUSUM detector, evidence-linked alerts, and synthetic evaluation/benchmark commands.

All event sources are explicitly `"simulated"`. Scenario labels exist to score evaluation only; feature extraction and detection read event type and timestamp counts, never labels. Alerts describe distribution changes, not malicious intent.

The initial project is an empty-workspace implementation created on Windows 11 / Python 3.14.3. Linux, WSL, native sensor integration, and production workloads have not been tested. The selected MIT license is in the repository root.
