from __future__ import annotations
from typing import Any

class VerificationError(RuntimeError):
    pass
class EntailmentError(VerificationError):
    pass
class CredibilityError(VerificationError):
    pass
class ContradictionError(VerificationError):
    pass
class TraceabilityError(VerificationError):
    pass
class GateRejected(VerificationError):
    def __init__(self, reason: str, report: dict[str, Any]):
        super().__init__(reason + ': ' + repr(report))
        self.reason = reason
        self.report = report
