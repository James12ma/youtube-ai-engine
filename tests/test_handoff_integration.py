"""Regressions in the assembled handoff, including credential boundaries."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from channel.oauth import authorize, oauth_status, UPLOAD_SCOPE


def test_oauth_consent_writes_private_token_without_upload(tmp_path):
    secrets=tmp_path/'client_secrets.json'
    secrets.write_text(json.dumps({'installed':{}}))
    token=tmp_path/'token.json'
    calls=[]
    credential=SimpleNamespace(has_scopes=lambda s:s==[UPLOAD_SCOPE],
                              to_json=lambda:'{"token":"TEST_ONLY"}')
    class Flow:
        def run_local_server(self, **kwargs):
            calls.append(kwargs)
            return credential
    def factory(path,scopes):
        assert scopes==[UPLOAD_SCOPE]
        return Flow()
    result=authorize(secrets,token,flow_factory=factory)
    assert result=={'authorized':True,'uploads_enabled':False}
    assert token.stat().st_mode & 0o777==0o600
    assert calls[0]['host']=='localhost' and calls[0]['port']==0
    with pytest.raises(ValueError,match='already exists'):
        authorize(secrets,token,flow_factory=factory)


def test_oauth_absent_is_offline(tmp_path):
    assert oauth_status(tmp_path/'absent.json')['configured'] is False


def test_oauth_sdk_inspects_without_network(tmp_path):
    pytest.importorskip('google.oauth2.credentials')
    path=tmp_path/'token.json'
    path.write_text(json.dumps({'token':'TEST_ONLY','refresh_token':'TEST_ONLY',
        'client_id':'TEST_ONLY','client_secret':'TEST_ONLY',
        'scopes':[UPLOAD_SCOPE]}))
    status=oauth_status(path)
    assert status['has_upload_scope'] and status['can_refresh']
    assert 'TEST_ONLY' not in json.dumps(status)


def test_narration_entrypoint_works_without_pythonpath():
    import os
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    result=subprocess.run([sys.executable,'-m','scripts.narration_smoke','--help'],
        capture_output=True,text=True,env=env)
    assert result.returncode==0


def test_draft_wires_owner_supplied_hostname_allowlist(tmp_path,monkeypatch):
    import channel.research as module
    monkeypatch.setenv('ROUTER_ALLOW_LIVE_API','1')
    monkeypatch.setenv('GROQ_API_KEY','TEST_ONLY')
    monkeypatch.setattr(module,'StateStore',lambda *a,**k:object())
    monkeypatch.setattr(module,'GroqAdapter',lambda:SimpleNamespace(close=lambda:None))
    monkeypatch.setattr(module,'Router',lambda *a:object())
    monkeypatch.setattr(module,'VerificationGate',lambda *a:object())
    class StopAtSources(RuntimeError):pass
    def pipeline(state,router,fetcher):
        assert fetcher._allowed_hosts=={'example.com','example.org'}
        fetcher._client.close()
        raise StopAtSources()
    monkeypatch.setattr(module,'ContentPipeline',pipeline)
    with pytest.raises(StopAtSources):
        module.generate_draft(tmp_path,'test',['https://example.com/a',
            'https://example.org/b'],tmp_path/'out',allow_live=True)
