"""One command for source-backed drafts. Live API calls require explicit authorization."""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from adapters import GroqAdapter,GeminiAdapter,OpenRouterAdapter
from pipeline import ContentPipeline,HttpSourceFetcher,QualityThresholds
from router import Router
from state_store import StateStore
from verification import VerificationGate
from verification.integrated import VerifiedContentPipeline


def generate_draft(repo:Path,topic:str,urls:list[str],out_dir:Path,*,
                   allow_live:bool=False,language:str='en',mode:str='tutorial')->dict:
    if language not in ('en','es') or mode not in ('tutorial','documentary'):
        raise ValueError('Unsupported language or content mode')
    if not allow_live or os.environ.get('ROUTER_ALLOW_LIVE_API')!='1':
        raise RuntimeError('LLM calls disabled; explicitly authorize free-only live API access')
    # These are the sources explicitly supplied by the owner, not a global
    # wildcard. HttpSourceFetcher still checks scheme, ports and private hosts.
    trusted_hosts={urlparse(url).hostname for url in urls}
    if not trusted_hosts or None in trusted_hosts:
        raise ValueError('Explicit HTTPS research sources required')
    state=StateStore(repo,push_required=True)
    adapters={}
    # Only configure free-tier API accounts with actually available keys.
    for provider,cls,key in (
        ('groq',GroqAdapter,'GROQ_API_KEY'),
        ('gemini',GeminiAdapter,'GEMINI_API_KEY'),
        ('openrouter',OpenRouterAdapter,'OPENROUTER_API_KEY')):
        if os.environ.get(key): adapters[provider]=cls()
    if not adapters:raise RuntimeError('No free-tier provider API key configured')
    try:
        router=Router(state,adapters)
        pipeline=VerifiedContentPipeline(ContentPipeline(
            state,router,HttpSourceFetcher(allowed_hosts=trusted_hosts),
            thresholds=QualityThresholds(language=language,
                packaging_style='growth' if mode=='documentary' else 'standard')),
            VerificationGate(router))
        result=pipeline.run(topic,urls)
    finally:
        for adapter in adapters.values():adapter.close()
    out_dir=Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):raise RuntimeError('Draft directory must be empty')
    out_dir.mkdir(parents=True,exist_ok=True)
    for name,value in (
        ('research',result.content.research),
        ('verification',result.content.verification),
        ('script',result.content.script),
        ('storyboard',result.content.storyboard),
        ('verification_gate',result.verification_gate.report)):
        (out_dir/f'{name}.json').write_text(value.model_dump_json(indent=2),encoding='utf-8')
    # ADVISORY only: the score is recorded for editorial review and never gates the draft.
    # A failure here must never lose or block a generated draft.
    try:
        from pipeline.hook_score import write_hook_advisory
        write_hook_advisory(result.content.script.hook,out_dir/'hook_advisory.json')
    except Exception as e:  # noqa: BLE001 - advisory must not affect the draft
        (out_dir/'hook_advisory.json').write_text(json.dumps({'advisory':True,'error':type(e).__name__}),encoding='utf-8')
    (out_dir/'STATUS.txt').write_text('RESEARCH GENERATED — HUMAN EDITORIAL REVIEW REQUIRED; NO PUBLISHING\n')
    return {'files':sorted(p.name for p in out_dir.iterdir()),'ready_for_publication':False}
