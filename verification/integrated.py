"""Explicit fail-closed facade; future production callers must use this entrypoint."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from .gate import GateOutcome, VerificationGate

@dataclass
class VerifiedPipelineResult:
    content: object
    verification_gate: GateOutcome
    ready_for_publication: bool = False  # Task 5 cannot authorize publishing

class VerifiedContentPipeline:
    def __init__(self, content_pipeline: object, verification_gate: VerificationGate):
        self._content = content_pipeline
        self._gate = verification_gate
    def run(self, topic: str, seed_urls: Sequence[str]) -> VerifiedPipelineResult:
        content = self._content.run(topic, seed_urls)
        gate = self._gate.run(content.research,content.verification,content.script,content.research.sources)
        return VerifiedPipelineResult(content=content,verification_gate=gate)
