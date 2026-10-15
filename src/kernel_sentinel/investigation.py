"""Optional, offline investigation-agent interface; no command execution surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kernel_sentinel.pipeline import Alert


@dataclass(frozen=True, slots=True)
class Investigation:
    hypotheses: tuple[str, ...]
    questions: tuple[str, ...]
    summary: str


class InvestigationAgent(Protocol):
    """Consumes structured evidence and returns text only; it cannot invoke tools."""

    def investigate(self, alert: Alert, evidence: tuple[dict[str, object], ...]) -> Investigation:
        """Return non-executable hypotheses, analyst questions, and a summary."""
