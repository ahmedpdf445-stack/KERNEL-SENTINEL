# Threat model

## Scope and assets

The MVP processes local synthetic or user-supplied JSONL. Relevant assets are analyst confidence in outputs, bounded host memory/CPU, event provenance, and integrity of evaluation labels. No credentials, network listener, privileged collector, command runner, or AI service is included.

## Trust boundaries and controls

- JSONL is untrusted: records are parsed as objects, timestamp/type/range/provenance checks apply, duplicate JSON keys and extra properties are rejected.
- State is bounded by graph event capacity; alert evidence and retained diagnostic strings have fixed caps. A single oversized input line can still consume transient memory in the caller/reader.
- Malformed records are counted with bounded retained messages. Invalid records are not converted into successful events.
- Scenario labels are kept out of the count detector; they are read only by evaluation.
- The optional investigation protocol returns hypotheses/questions/text and exposes no execution function. Its implementer must also be treated as untrusted if one is later added.
- Statistical alerts are explanatory anomaly indicators, not verdicts. Review evidence and collection quality before acting.

## Out of scope / residual risks

This is not a secure multi-tenant ingestion service. It has no authentication, transport security, durable audit log, privacy controls, quotas, or hostile-input resource isolation. Forged records can affect local analysis; a malicious stream can cause computational work up to graph capacity and can exploit arbitrarily long line allocation upstream. Synthetic source validation is not cryptographic provenance. There is no live sensor or operating-system trust boundary to assess.

Report vulnerabilities using [SECURITY.md](../SECURITY.md).
