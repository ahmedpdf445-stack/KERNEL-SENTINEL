# Contributing

Contributions should preserve the simulated-only boundary and standard-library runtime. Keep scenario labels out of detector inputs, add focused `unittest` coverage for behavior changes, and update directly affected documentation. Do not claim live telemetry or benchmark performance without reproducible evidence.

Run the suite from PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\src"; python -m unittest discover -s tests -v
```

Use deterministic seeds in tests, explicit event/loss provenance, bounded state, and meaningful error reporting. Review [the threat model](docs/THREAT_MODEL.md) and [limitations](docs/LIMITATIONS.md) before proposing sensor or service features.
