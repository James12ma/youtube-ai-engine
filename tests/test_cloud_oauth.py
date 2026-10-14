import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from channel.oauth import (load_upload_credentials, OAuthConfigurationError,
                           SECRET_NAMES, TOKEN_URI, UPLOAD_SCOPE)


class CloudOAuthTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(zip(SECRET_NAMES, ('client', 'secret', 'refresh')))
        self.creds = Mock(valid=False, granted_scopes=[UPLOAD_SCOPE])
        self.creds.to_json.return_value = json.dumps({'token':'refreshed','refresh_token':'refresh'})
        self.factory = Mock(return_value=self.creds)
        self.factory.from_authorized_user_info.return_value = self.creds
        self.transport = Mock(return_value='response')
        def refresh(request):
            request(url=TOKEN_URI, method='POST', body=b'private')
            self.creds.valid = True
        self.creds.refresh.side_effect = refresh

    def load(self, path=None):
        return load_upload_credentials(path, environment=self.env,
            credentials_factory=self.factory, request_factory=lambda: self.transport)

    def test_cloud_refresh_uses_google_endpoint_scope_and_timeout(self):
        self.assertIs(self.load(), self.creds)
        self.assertEqual(self.factory.call_args.kwargs['token_uri'], TOKEN_URI)
        self.assertEqual(self.factory.call_args.kwargs['scopes'], [UPLOAD_SCOPE])
        self.assertEqual(self.transport.call_args.kwargs['timeout'], 30)

    def test_missing_secret_never_refreshes(self):
        self.env.pop(SECRET_NAMES[2])
        with self.assertRaises(OAuthConfigurationError): self.load()
        self.creds.refresh.assert_not_called()

    def test_whitespace_secret_rejected(self):
        self.env[SECRET_NAMES[1]] = ' '
        with self.assertRaises(OAuthConfigurationError): self.load()
        self.creds.refresh.assert_not_called()

    def test_provider_error_cannot_leak_secrets(self):
        self.creds.refresh.side_effect = RuntimeError('secret refresh private provider body')
        with self.assertRaises(OAuthConfigurationError) as result: self.load()
        self.assertNotIn('private provider', str(result.exception))
        self.assertIsNone(result.exception.__cause__)
        self.assertTrue(result.exception.__suppress_context__)

    def test_allowlisted_error_code_only(self):
        self.creds.refresh.side_effect = RuntimeError('secret provider body',
            {'error':'invalid_client','error_description':'private client secret'})
        with self.assertRaises(OAuthConfigurationError) as result: self.load()
        self.assertEqual(str(result.exception),'OAuth token request failed: invalid_client')

    def test_unknown_error_body_not_logged(self):
        self.creds.refresh.side_effect = RuntimeError('secret', {'error':'private-token-value'})
        with self.assertRaises(OAuthConfigurationError) as result: self.load()
        self.assertNotIn('private-token-value',str(result.exception))

    def test_missing_granted_scope_fails(self):
        self.creds.granted_scopes = ['https://www.googleapis.com/auth/userinfo.email']
        with self.assertRaisesRegex(OAuthConfigurationError, 'scope'): self.load()

    def test_omitted_scope_response_is_not_claimed_confirmed(self):
        self.creds.granted_scopes = None
        self.assertIsNone(self.load().granted_scopes)

    def test_file_precedence_refreshed_atomic_mode_0600(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'token.json';p.write_text(json.dumps({'token_uri':TOKEN_URI}))
            self.env={}
            self.load(p)
            self.factory.assert_not_called()
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(p.read_text())['token'],'refreshed')

    def test_custom_endpoint_rejected_before_refresh(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'token.json';p.write_text(json.dumps({'token_uri':'https://example.invalid/token'}))
            with self.assertRaises(OAuthConfigurationError): self.load(p)
            self.creds.refresh.assert_not_called()

    def test_valid_file_reuses_access_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'token.json';p.write_text('{}')
            self.creds.valid=True
            self.load(p)
            self.creds.refresh.assert_not_called()


if __name__ == '__main__': unittest.main()
