"""Router-specific exceptions."""
from __future__ import annotations
class RouterError(RuntimeError): pass
class AllProvidersFailed(RouterError): pass
class RouterPaused(RouterError): pass
class LiveAPINotAuthorized(RouterError): pass
class BillableModelRejected(RouterError): pass
