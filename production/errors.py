class ProductionError(RuntimeError): pass
class FFmpegMissingError(ProductionError): pass
class TTSUnavailableError(ProductionError): pass
class RenderError(ProductionError): pass
class VerifyError(ProductionError): pass
class UnsafeVisualError(ProductionError): pass
