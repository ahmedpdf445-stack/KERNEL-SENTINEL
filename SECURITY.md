# Security policy

Kernel Sentinel is a local research MVP, not a production security product. Do not send real sensitive telemetry to third-party services through this project; none is required or integrated.

To report a vulnerability, contact the repository maintainers through a private channel before public disclosure. Include the affected version/commit, reproduction steps, impact, and a suggested mitigation when available. Do not include credentials or unrelated personal data in a report.

The parser rejects malformed/unknown telemetry fields and bounds retained graph and diagnostic state, but it is not designed as a hardened public ingestion service. See [the threat model](docs/THREAT_MODEL.md).
