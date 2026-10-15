import json
from types import SimpleNamespace
from unittest.mock import Mock
import httpx
import pytest
from channel.oauth import (cloud_secret_diagnostics, SECRET_NAMES, UPLOAD_SCOPE,
                           READONLY_SCOPE, load_upload_credentials, OAuthConfigurationError)
from scripts.check_cloud_oauth import check_channel


def test_diagnostics_never_include_credential_values():
    env=dict(zip(SECRET_NAMES, ('123-abc.apps.googleusercontent.com','GOCSPX-private','1//private')))
    report=cloud_secret_diagnostics(env)
    assert all(isinstance(v,bool) for v in report.values())
    assert report['client_id_format_valid'] and report['all_required_present']
    assert not any(secret in json.dumps(report) for secret in env.values())
    env[SECRET_NAMES[1]]=env[SECRET_NAMES[0]]
    assert cloud_secret_diagnostics(env)['client_secret_equals_client_id']


def test_only_requested_granted_scopes_accepted():
    creds=Mock(valid=True,granted_scopes=[UPLOAD_SCOPE])
    factory=Mock(return_value=creds)
    with pytest.raises(OAuthConfigurationError,match='scope'):
        load_upload_credentials(environment=dict.fromkeys(SECRET_NAMES,'dummy'),
            credentials_factory=factory, scopes=(UPLOAD_SCOPE,READONLY_SCOPE))
    creds.refresh.assert_not_called()


def test_unknown_scope_rejected_before_credentials():
    factory=Mock()
    with pytest.raises(OAuthConfigurationError):
        load_upload_credentials(credentials_factory=factory,scopes=('unexpected',))
    factory.assert_not_called()


def test_malformed_provider_error_is_sanitized():
    creds=Mock(valid=False)
    creds.refresh.side_effect=RuntimeError('private',{'error':{'private':'token'}})
    with pytest.raises(OAuthConfigurationError) as result:
        load_upload_credentials(environment=dict.fromkeys(SECRET_NAMES,'dummy'),
            credentials_factory=Mock(return_value=creds),request_factory=Mock())
    assert 'private' not in str(result.value)


def test_channel_verification_is_read_only_and_checks_owner_id():
    requests=[]
    def respond(request):
        requests.append(request)
        assert request.headers['Authorization']=='Bearer private'
        return httpx.Response(200,json={'items':[{'id':'UC_example','snippet':{'title':'Original channel'}}]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        good=check_channel(SimpleNamespace(token='private'),client=client,expected_channel_id='UC_example')
        wrong=check_channel(SimpleNamespace(token='private'),client=client,expected_channel_id='UC_other')
    assert good['verified'] and not wrong['verified']
    assert all(r.method=='GET' and r.url.path=='/youtube/v3/channels' for r in requests)
    assert 'private' not in json.dumps(good)


def test_channel_failure_does_not_echo_provider_response():
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(403,text='private-token'))) as client:
        result=check_channel(SimpleNamespace(token='private'),client=client)
    assert result=={'verified':False,'http_status':403}
