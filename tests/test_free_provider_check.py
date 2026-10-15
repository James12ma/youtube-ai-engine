import httpx
from scripts.check_free_providers import zero_priced_model, inspect_provider, run


def test_model_must_be_explicitly_free_and_all_prices_zero():
    model={'id':'provider/example:free','pricing':{'prompt':'0','completion':'0','request':'0'}}
    assert zero_priced_model(model)
    assert not zero_priced_model({**model,'id':'provider/paid'})
    assert not zero_priced_model({**model,'pricing':{'prompt':'0','completion':'0','request':'0.01'}})
    assert not zero_priced_model({**model,'pricing':{'prompt':'0'}})


def test_readonly_failure_does_not_echo_body():
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(401,text='private'))) as client:
        result=inspect_provider(client,'https://example.invalid/models',{},'model')
    assert result=={'authenticated':False,'http_status':401}


def test_unverified_billing_prevents_every_generation_request(tmp_path,monkeypatch):
    for name in ('GROQ_API_KEY','GEMINI_API_KEY'):monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY','private')
    requests=[]
    def respond(r):
        requests.append(r)
        return httpx.Response(200,json={'data':{'is_free_tier':False}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result=run(tmp_path,client=client)
    assert not result['openrouter'].get('generation_attempted')
    assert all(r.method=='GET' for r in requests)
    assert 'private' not in (tmp_path/'provider_report.json').read_text()


def test_free_quota_exhausted_does_not_generate(tmp_path,monkeypatch):
    for name in ('GROQ_API_KEY','GEMINI_API_KEY'):monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY','private')
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'data':{
        'is_free_tier':True,'free_model_daily_requests':{'remaining':0}}}))) as client:
        result=run(tmp_path,client=client)
    assert result['openrouter']['blocked']=='Free request quota exhausted'
