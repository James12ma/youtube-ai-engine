"""Read-only key checks and up to three explicitly zero-priced routing attempts.

Never sends generation requests to accounts whose no-cost status is unverified.
No provider response bodies or credentials are printed on failure.
"""
from __future__ import annotations
import json, os, subprocess, tempfile, re
from pathlib import Path
from decimal import Decimal, InvalidOperation
from dataclasses import replace
import httpx
from pydantic import BaseModel, Field
from adapters import OpenRouterAdapter, LLMRequest
from adapters.config import OPENROUTER_CONFIG
from router import Router, RouterConfig
from state_store import StateStore


class DemoScript(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    narration: str = Field(min_length=50, max_length=1500)
    requires_owner_review: bool


def zero_priced_model(model):
    prices=model.get('pricing', {})
    if not isinstance(model.get('id'),str) or not model['id'].endswith(':free'):
        return False
    if not all(key in prices for key in ('prompt','completion')): return False
    try: return all(Decimal(str(value)) == 0 for value in prices.values())
    except (InvalidOperation,TypeError,ValueError): return False


def inspect_provider(client, url, headers, wanted_model):
    try:
        r=client.get(url,headers=headers)
        if r.status_code!=200:return {'authenticated':False,'http_status':r.status_code}
        body=r.json();models=body.get('data',body.get('models',[]))
        ids={m.get('id',m.get('name','').removeprefix('models/')) for m in models if isinstance(m,dict)}
        return {'authenticated':True,'configured_model_present':wanted_model in ids,
                'generation_enabled':False,'billing_verified_free':False}
    except Exception:return {'authenticated':False,'error':'Read-only metadata check failed'}


def run(output_dir:Path, *, client=None):
    output_dir.mkdir(parents=True,exist_ok=True)
    report={'publishing_enabled':False,'uploads_enabled':False,'paid_calls':0,'generation_requests_max':3}
    own=client is None;client=client or httpx.Client(timeout=30,follow_redirects=False)
    try:
        for name,url,key,header,model in [
            ('groq','https://api.groq.com/openai/v1/models','GROQ_API_KEY','Authorization','openai/gpt-oss-120b'),
            ('gemini','https://generativelanguage.googleapis.com/v1beta/models','GEMINI_API_KEY','x-goog-api-key','gemini-2.5-flash')]:
            secret=os.environ.get(key,'')
            report[name]=inspect_provider(client,url,{header:('Bearer '+secret) if header=='Authorization' else secret},model) if secret else {'authenticated':False,'missing_key':True}
        key=os.environ.get('OPENROUTER_API_KEY','')
        if not key:report['openrouter']={'authenticated':False,'missing_key':True};return report
        response=client.get('https://openrouter.ai/api/v1/key',headers={'Authorization':'Bearer '+key})
        if response.status_code!=200:
            report['openrouter']={'authenticated':False,'http_status':response.status_code};return report
        account=response.json().get('data',{})
        report['openrouter']={'authenticated':True,'is_free_tier':account.get('is_free_tier') is True}
        # The owner authorized limited free calls; additionally verify this account is free.
        if account.get('is_free_tier') is not True:
            report['openrouter']['blocked']='Free-tier account status not established';return report
        remaining=account.get('free_model_daily_requests',{}).get('remaining')
        if remaining is not None and remaining<1:
            report['openrouter']['blocked']='Free request quota exhausted';return report
        catalog=client.get('https://openrouter.ai/api/v1/models')
        catalog.raise_for_status()
        free=[m for m in catalog.json().get('data',[]) if zero_priced_model(m)
              and 'response_format' in m.get('supported_parameters',[])]
        if not free:report['openrouter']['blocked']='No zero-priced JSON-capable free model available';return report
        free.sort(key=lambda m:(m['id']!=OPENROUTER_CONFIG.default_model,
            'instruct' not in m['id'].lower(), 'preview' in m['id'].lower(),m['id']))
        candidates=free[:min(3,remaining) if isinstance(remaining,int) else 3]
        report['openrouter']['attempts']=[]
        # State is isolated to this integration test; production state branch is untouched.
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)/'state';repo.mkdir()
            def git(*args):subprocess.run(['git',*args],cwd=repo,check=True,capture_output=True)
            git('init','-b','main');git('config','user.name','Engine verification');git('config','user.email','verification@example.invalid')
            (repo/'README.md').write_text('Isolated zero-cost integration state\n')
            git('add','.');git('commit','-m','Initialize isolated verification')
            old={k:os.environ.get(k) for k in ('ENABLE_LIVE_LLM','ROUTER_ALLOW_LIVE_API')}
            os.environ['ENABLE_LIVE_LLM']='1';os.environ['ROUTER_ALLOW_LIVE_API']='1'
            try:
                for candidate in candidates:
                    selected=candidate['id'];attempt={'model':selected,'http_status':None}
                    def record_status(response):attempt['http_status']=response.status_code
                    wire=httpx.Client(timeout=40,follow_redirects=False,event_hooks={'response':[record_status]})
                    adapter=None
                    try:
                        cfg=replace(OPENROUTER_CONFIG,default_model=selected,max_retries=1,request_timeout=40)
                        adapter=OpenRouterAdapter(config=cfg,client=wire)
                        engine=Router(StateStore(repo,push_required=False),{'openrouter':adapter},
                            RouterConfig(provider_order=('openrouter',),all_failed_pause=0,
                                rpd={'openrouter':3},rpm={'openrouter':3}))
                        request=LLMRequest(model=selected,max_tokens=1500,schema=DemoScript,messages=[{'role':'user','content':
                            'Write a short English narration for our ORIGINAL local expense rule demo. Example inputs: travel 120 dollars needs manager review; travel 80 dollars is auto-approved. These are demo inputs, not revenue claims. Include owner review required. Return JSON with title, narration, requires_owner_review=true. Do not claim real business results.'}])
                        result=engine.execute('integration-script',{'demo':'original expense rules'},request,DemoScript)
                        if result.requires_owner_review is not True:raise ValueError('Owner review flag absent')
                        cached=engine.execute('integration-script',{'demo':'original expense rules'},request,DemoScript)
                        assert result==cached
                        (output_dir/'ai_script_draft.json').write_text(result.model_dump_json(indent=2))
                        report['openrouter'].update(model=selected,router_succeeded=True,durable_cache_reused=True,
                            generation_attempted=True,review_required=True,all_model_prices_verified_zero=True)
                        attempt['passed']=True
                    except Exception as exc:
                        attempt.update(passed=False,error_type=type(exc).__name__)
                        known=re.search(r'\b(RateLimitError|AuthError|ClientError|SchemaValidationError|ServerError|BillableModelRejected)\b',str(exc))
                        if known:attempt['classified_failure']=known.group(1)
                        report['openrouter'].update(router_succeeded=False,generation_attempted=True)
                    finally:
                        if adapter:adapter.close()
                        else:wire.close()
                        report['openrouter']['attempts'].append(attempt)
                    if attempt['passed']:break
            finally:
                for name,value in old.items():
                    if value is None:os.environ.pop(name,None)
                    else:os.environ[name]=value
    except Exception:
        report['error']='Provider inspection failed; sensitive details suppressed'
    finally:
        if own:client.close()
        (output_dir/'provider_report.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    report=run(Path('outputs/free-provider-check'))
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report.get('openrouter',{}).get('router_succeeded') else 1)
