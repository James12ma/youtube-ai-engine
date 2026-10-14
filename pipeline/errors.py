from __future__ import annotations
from typing import Any
class PipelineError(RuntimeError): pass
class InsufficientSourcesError(PipelineError): pass
class PipelineQualityError(PipelineError):
    def __init__(self, stage: str, report: dict[str, Any]) -> None:
        super().__init__('Stage ' + stage + ' failed quality gate: ' + repr(report))
        self.stage = stage
        self.report = report
class PublishingDisabledError(PipelineError): pass
