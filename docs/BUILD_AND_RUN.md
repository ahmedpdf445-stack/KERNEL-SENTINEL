# Build and run

## Requirements

Python 3.11+; standard library only for runtime and tests. No native build step is required. The checked environment was Windows 11 with CPython 3.14.3.

## Virtual environment

```powershell
cd "E:\FX\C.D\KERNEL SENTINEL"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\src"
```

Activation is optional; the equivalent is to prefix `python` with `.\.venv\Scripts\python.exe`. No package download is needed for direct module execution. `pip install -e .` optionally installs the `kernel-sentinel` command using the declared setuptools build backend.

## Operations

```powershell
python -m kernel_sentinel --help
python -m kernel_sentinel simulate --seed 42 --buckets 120 --scenario mixed --output .\reports\sample.jsonl
python -m kernel_sentinel detect .\reports\sample.jsonl --window 30 --min-samples 10 --allowance 0.5 --threshold 5
python -m kernel_sentinel evaluate --seed 4242 --buckets 180 --output .\reports\evaluation.json
python -m kernel_sentinel benchmark --seed 2025 --buckets 1000 --output .\reports\performance.json
```

Use `-` for stdin/stdout. Simulator status is sent to stderr; `detect` emits JSON alerts and one summary record to stdout. `detect` skips malformed lines while reporting their count and a bounded list of validation messages. An incomplete stream (malformed data, loss, ordering/graph integrity issue, or graph-capacity exhaustion) is marked in the summary and exits with code 2; capacity exhaustion halts further processing. A file-open failure or invalid CLI configuration also exits with code 2.
