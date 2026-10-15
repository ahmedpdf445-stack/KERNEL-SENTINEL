"""Generate the repository's architecture SVG using only Python's standard library."""

from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET


def make_svg() -> str:
    boxes = [
        (30, 70, 185, 92, "Deterministic simulator", "seeded synthetic events"),
        (260, 70, 185, 92, "JSONL validation", "events + loss reports"),
        (490, 70, 185, 92, "Streaming pipeline", "bounded process graph"),
        (720, 70, 185, 92, "Detection engine", "rolling baseline + CUSUM"),
        (950, 70, 185, 92, "Explainable alerts", "evidence event IDs"),
        (490, 250, 185, 92, "Evaluation suite", "independent labelled data"),
        (720, 250, 185, 92, "CLI + benchmarks", "local; no external service"),
    ]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="390" viewBox="0 0 1180 390">',
             '<rect width="100%" height="100%" fill="#f8fafc"/>',
             '<style>text{font-family:Segoe UI,Arial,sans-serif}.title{font-size:21px;font-weight:700;fill:#0f172a}.label{font-size:15px;font-weight:600;fill:#0f172a}.sub{font-size:12px;fill:#475569}.edge{stroke:#475569;stroke-width:2;fill:none;marker-end:url(#arrow)}</style>',
             '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L9,4 L0,8 z" fill="#475569"/></marker></defs>',
             '<text x="30" y="35" class="title">KERNEL SENTINEL — Python-only research MVP</text>']
    for x1, x2 in ((215, 260), (445, 490), (675, 720), (905, 950)):
        parts.append(f'<path d="M{x1} 116 H{x2}" class="edge"/>')
    parts.extend(['<path d="M582 162 V215 H812 V250" class="edge"/>',
                  '<path d="M812 162 V250" class="edge"/>',
                  '<path d="M582 162 V250" class="edge"/>'])
    for x, y, width, height, title, sub in boxes:
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="#e0f2fe" stroke="#0284c7" stroke-width="2"/>')
        parts.append(f'<text x="{x + width / 2}" y="{y + 38}" text-anchor="middle" class="label">{escape(title)}</text>')
        parts.append(f'<text x="{x + width / 2}" y="{y + 63}" text-anchor="middle" class="sub">{escape(sub)}</text>')
    parts.append('<text x="30" y="365" class="sub">All telemetry is explicitly simulated; no live kernel sensor is implemented.</text></svg>')
    svg = "\n".join(parts) + "\n"
    ET.fromstring(svg)
    return svg


def make_process_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="920" height="330" viewBox="0 0 920 330">
<rect width="100%" height="100%" fill="#f8fafc"/>
<style>text{font-family:Segoe UI,Arial,sans-serif}.title{font-size:21px;font-weight:700;fill:#0f172a}.label{font-size:14px;font-weight:600;fill:#0f172a}.sub{font-size:12px;fill:#475569}.edge{stroke:#475569;stroke-width:2;fill:none;marker-end:url(#arrow)}</style>
<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L9,4 L0,8 z" fill="#475569"/></marker></defs>
<text x="30" y="35" class="title">Process generations: PID is not a lifetime identity</text>
<rect x="60" y="90" width="200" height="78" rx="10" fill="#e0f2fe" stroke="#0284c7" stroke-width="2"/>
<text x="160" y="120" text-anchor="middle" class="label">PID 1000 @ root-start</text>
<text x="160" y="145" text-anchor="middle" class="sub">root generation</text>
<rect x="350" y="90" width="230" height="78" rx="10" fill="#dcfce7" stroke="#16a34a" stroke-width="2"/>
<text x="465" y="120" text-anchor="middle" class="label">PID 1001 @ child-start-A</text>
<text x="465" y="145" text-anchor="middle" class="sub">event IDs map to this identity</text>
<path d="M260 128 H350" class="edge"/>
<rect x="350" y="218" width="230" height="78" rx="10" fill="#fef3c7" stroke="#d97706" stroke-width="2"/>
<text x="465" y="248" text-anchor="middle" class="label">PID 1001 @ child-start-B</text>
<text x="465" y="273" text-anchor="middle" class="sub">new generation; PID reused</text>
<path d="M260 145 C300 200 310 250 350 256" class="edge"/>
<path d="M600 128 H680" class="edge"/>
<rect x="690" y="90" width="190" height="78" rx="10" fill="#f1f5f9" stroke="#64748b" stroke-width="2"/>
<text x="785" y="120" text-anchor="middle" class="label">evidence event IDs</text>
<text x="785" y="145" text-anchor="middle" class="sub">retain original ancestry</text>
<text x="30" y="320" class="sub">Synthetic start-event IDs model generations only; real OS identity needs host/boot and namespace context.</text>
</svg>
"""


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "docs" / "diagrams"
    root.mkdir(parents=True, exist_ok=True)
    for filename, contents in (
        ("architecture.svg", make_svg()),
        ("process-identity.svg", make_process_svg()),
    ):
        ET.fromstring(contents)
        target = root / filename
        target.write_text(contents, encoding="utf-8")
        print(target)
