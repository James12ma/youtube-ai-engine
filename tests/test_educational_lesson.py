import json
from pathlib import Path
import httpx
import pytest
from scripts.diagnose_free_quota import classify

@pytest.mark.parametrize('message,flag',[
    ('free-models-per-day limit exceeded','daily_quota_exhausted'),
    ('Model is temporarily rate-limited upstream','upstream_capacity'),
    ('Requests per minute exceeded','minute_rate_limit'),
])
def test_rate_reason_is_fixed_vocabulary(message,flag):
    response=httpx.Response(429,json={'error':{'message':message,'metadata':{'raw':'secret-value-not-for-output','provider_name':'arbitrary-secret'}}},headers={'Retry-After':'30'})
    result=classify(response)
    assert result[flag] and result['retry_after_seconds']==30
    assert 'secret' not in json.dumps(result)


def test_lesson_has_substantive_script_and_real_demo_expectations():
    lesson=json.loads(Path('content/expense-rule-lesson/lesson.json').read_text())
    assert sum(len(c['narration'].split()) for c in lesson['chapters'])>800
    demos=[c['demo'] for c in lesson['chapters'] if c['demo']]
    assert ['100','travel','AUTO-APPROVED'] in demos
    assert ['100.01','travel','SENT FOR MANAGER REVIEW'] in demos
    assert len(demos)>=7
    assert 'not output' in lesson['provenance']


def test_cohere_prompt_json_is_still_schema_validated():
    from adapters import OpenRouterAdapter,LLMRequest
    from adapters.errors import SchemaValidationError
    from scripts.check_free_providers import DemoScript
    captured=[]
    def wire(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'not valid JSON'}}]})
    with OpenRouterAdapter(api_key='TEST_ONLY',transport=httpx.MockTransport(wire)) as adapter:
        with pytest.raises(SchemaValidationError):adapter.complete(LLMRequest(model='cohere/north-mini-code:free',schema=DemoScript,messages=[{'role':'user','content':'Return JSON'}]))
    assert 'response_format' not in captured[0]
    assert captured[0]['reasoning']=={'enabled':False}
    assert 'JSON Schema' in captured[0]['messages'][0]['content']


def test_quota_metadata_diagnosis_never_sends_generation(tmp_path,monkeypatch):
    import scripts.diagnose_free_quota as module
    import httpx
    calls=[]
    def handler(request):
        calls.append((request.method,str(request.url)))
        assert request.method=='GET'
        return httpx.Response(200,json={'data':{'is_free_tier':True,
            'free_model_daily_requests':{'limit':50,'used':45,'remaining':5}}})
    client=httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(module.httpx,'Client',lambda **kw:client)
    monkeypatch.setenv('OPENROUTER_API_KEY','offline-placeholder')
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    report=module.run(tmp_path/'report',metadata_only=True)
    assert report['daily_requests']['remaining']==5
    assert report['attempts']==[] and report['metadata_only'] is True
    assert calls==[('GET','https://openrouter.ai/api/v1/key')]


def test_provider_metadata_reports_only_safe_statuses_and_never_generates(tmp_path,monkeypatch):
    import scripts.diagnose_free_quota as module
    import httpx
    calls=[]
    def handler(request):
        calls.append(request.method)
        assert request.method=='GET'
        if request.url.host=='openrouter.ai':
            return httpx.Response(200,json={'data':{'is_free_tier':True,'free_model_daily_requests':{'remaining':38}}})
        if request.url.host=='api.groq.com':
            return httpx.Response(401,json={'error':{'message':'PRIVATE_DO_NOT_ECHO'}})
        return httpx.Response(200,json={'models':[{'name':'models/gemini-2.5-flash'}]})
    client=httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(module.httpx,'Client',lambda **kw:client)
    for key in ('OPENROUTER_API_KEY','GROQ_API_KEY','GEMINI_API_KEY'):
        monkeypatch.setenv(key,'PRIVATE_KEY_DO_NOT_ECHO')
    report=module.run(tmp_path/'report',metadata_only=True)
    assert report['other_providers']['groq']['http_status']==401
    assert report['other_providers']['gemini']['configured_model_present'] is True
    assert calls==['GET','GET','GET']
    assert 'PRIVATE' not in __import__('json').dumps(report)
