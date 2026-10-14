class ProError(RuntimeError): pass
class RecorderError(ProError): pass
class NarrationError(ProError): pass
class ChartError(ProError): pass
class EditingError(ProError): pass
class QCFailure(ProError):
    def __init__(self, failures, report=None):
        self.failures = failures
        self.report = report or {}
        super().__init__('; '.join(failures))
