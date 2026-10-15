"""Bounded zero-price live diagnosis. Never logs raw error bodies or credentials."""
import json, os
from pathlib import Path
import httpx
from scripts.check_free_providers import zero_priced_model


def classify(response):
    result={'http_status':response.status_code}
    try:
        error=response.json().get('error',{})
        metadata=error.get('metadata',{})
        message=(str(error.get('message',''))+' '+str(metadata.get('raw',''))).lower()
        for flag,phrases in {
            'daily_quota_exhausted':['free-models-per-day','daily limit','daily quota','per day'],
            'minute_rate_limit':['per-minute','per minute','requests per minute'],
            'upstream_capacity':['rate-limited upstream','upstream_provider_shared_pool','temporarily rate limited','temporarily rate-limited'],
            'insufficient_credit':['insufficient credits','insufficient balance']}.items():
            result[flag]=any(p in message for p in phrases)
        for key in ('limit_source','provider_name'):
            value=metadata.get(key)
            # Fixed vocabulary: never echo arbitrary provider response text.
            if value in ('upstream_provider_shared_pool','openrouter','OpenRouter','Google AI Studio','Google Vertex','DeepInfra','Together','ModelRun','Chutes','Nvidia'):
                result[key]=value
        retry=response.headers.get('retry-after','')
        if retry.isdigit():result['retry_after_seconds']=int(retry)
    except (ValueError,TypeError,AttributeError):result['classification_unavailable']=True
    return result


def run(out=Path('outputs/quota-diagnosis')):
    out.mkdir(parents=True,exist_ok=True)
    report={'paid_calls':0,'uploads':0,'attempts':[]}
    key=os.environ.get('OPENROUTER_API_KEY','')
    if not key:raise RuntimeError('Missing OpenRouter key; value suppressed')
    with httpx.Client(timeout=60,follow_redirects=False) as client:
        headers={'Authorization':'Bearer '+key}
        auth=client.get('https://openrouter.ai/api/v1/key',headers=headers)
        auth.raise_for_status();data=auth.json().get('data',{})
        report['free_tier_confirmed']=data.get('is_free_tier') is True
        quota=data.get('free_model_daily_requests',{})
        report['daily_requests']={k:v for k,v in quota.items() if k in ('limit','remaining','used') and isinstance(v,(int,float))}
        if not report['free_tier_confirmed']:raise RuntimeError('Unverified free account; no generation allowed')
        if quota.get('remaining',1)<1:
            report['blocked']='account_daily_quota';(out/'report.json').write_text(json.dumps(report,indent=2));return report
        catalog=client.get('https://openrouter.ai/api/v1/models');catalog.raise_for_status()
        models=[m['id'] for m in catalog.json()['data'] if zero_priced_model(m)]
        preferred='google/gemma-4-26b-a4b-it:free'
        candidates=([preferred] if preferred in models else [])+[m for m in sorted(models) if m!=preferred][:2]
        for model in candidates[:3]:
            response=client.post('https://openrouter.ai/api/v1/chat/completions',headers=headers,json={
                'model':model,'max_tokens':160,'temperature':0,'messages':[{'role':'user','content':'Explain in two sentences why an expense approval rule should test the exact threshold and the smallest accepted amount above it. Do not invent statistics.'}]})
            attempt={'model':model,**classify(response)}
            if response.status_code==200:
                body=response.json();text=body.get('choices',[{}])[0].get('message',{}).get('content','')
                if not isinstance(text,str) or not text.strip():attempt['usable_output']=False
                else:
                    attempt['usable_output']=True
                    (out/('response_'+str(len(report['attempts']))+'.txt')).write_text(text)
            report['attempts'].append(attempt)
            if response.status_code==429:
                # Only model-specific upstream saturation permits a different model.
                if not attempt.get('upstream_capacity') or attempt.get('daily_quota_exhausted') or attempt.get('minute_rate_limit'):
                    report['blocked']='global_or_unclassified_rate_limit';break
            elif response.status_code!=200:break
        (out/'report.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':print(json.dumps(run(),indent=2))
