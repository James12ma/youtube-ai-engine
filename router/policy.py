"""Fail-closed model names for controlled smoke tests.

An allowlisted name is NOT proof that an account cannot be billed. Real calls
still require the owner to confirm provider billing settings separately.
"""
from __future__ import annotations
from .errors import BillableModelRejected
APPROVED = {
    'groq': frozenset({'openai/gpt-oss-120b', 'openai/gpt-oss-20b'}),
    'gemini': frozenset({'gemini-2.5-flash', 'gemini-3.1-flash-lite'}),
}
def is_free_model(provider: str, model: str) -> bool:
    if provider == 'openrouter':
        return bool(model and model.endswith(':free') and not model.startswith(':'))
    return model in APPROVED.get(provider, ())
def require_free_model(provider: str, model: str) -> None:
    if not is_free_model(provider, model):
        raise BillableModelRejected(f'Model {model!r} for {provider!r} is not approved')
