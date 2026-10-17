"""Refresh owner OAuth in cloud, print only readiness booleans. Never uploads."""
import json
import os
from channel.oauth import (load_upload_credentials, OAuthConfigurationError,
                           UPLOAD_SCOPE, READONLY_SCOPE, cloud_secret_diagnostics)

NEXT_ACTIONS = {
    'invalid_client': 'Check the current Web OAuth client ID and its matching client secret in GitHub Secrets; replacing only the refresh token cannot fix client authentication.',
    'unauthorized_client': 'Verify the OAuth client type and that the refresh token was issued to this same active client.',
    'invalid_grant': 'Reauthorize the same client; the refresh token may be revoked, expired or issued to another client.',
    'invalid_scope': 'Authorize youtube.upload and youtube.readonly together for the same client.',
}


def check_channel(credentials, *, client=None, expected_channel_id=None):
    """Read-only channels.list; no upload, insert, update or delete endpoint."""
    import httpx
    owned = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        response = client.get('https://www.googleapis.com/youtube/v3/channels',
            params={'part': 'id,snippet', 'mine': 'true'},
            headers={'Authorization': 'Bearer ' + credentials.token})
        if response.status_code != 200:
            return {'verified': False, 'http_status': response.status_code}
        items = response.json().get('items', [])
        channels = [{'id': item['id'], 'title': item.get('snippet', {}).get('title', '')}
                    for item in items if isinstance(item, dict) and isinstance(item.get('id'), str)]
        matches = not expected_channel_id or any(c['id'] == expected_channel_id for c in channels)
        return {'verified': bool(channels) and matches, 'channels': channels,
                'expected_channel_configured': bool(expected_channel_id),
                'expected_channel_matches': matches if expected_channel_id else None}
    except Exception:
        return {'verified': False, 'error': 'Channel verification failed; response details suppressed'}
    finally:
        if owned: client.close()


def main():
    report = {'uploads_enabled': False, 'publications_enabled': False,
              'live_llm_calls': 0,
              'secret_diagnostics': cloud_secret_diagnostics(),
              'provider_key_present': {name: bool(os.environ.get(name)) for name in
                  ('GROQ_API_KEY', 'GEMINI_API_KEY', 'OPENROUTER_API_KEY')}}
    try:
        credentials = load_upload_credentials(scopes=(UPLOAD_SCOPE, READONLY_SCOPE))
        report.update(oauth_refresh_succeeded=True, access_token_valid=credentials.valid,
                      upload_scope_requested=True,
                      upload_scope_confirmed=(UPLOAD_SCOPE in credentials.granted_scopes)
                          if credentials.granted_scopes is not None else None)
        report['channel_access'] = check_channel(credentials,
            expected_channel_id=os.environ.get('YOUTUBE_EXPECTED_CHANNEL_ID'))
        code = 0 if report['channel_access']['verified'] else 1
    except OAuthConfigurationError as exc:
        report.update(oauth_refresh_succeeded=False, error=str(exc))
        report['error_code'] = exc.code
        report['next_action'] = NEXT_ACTIONS.get(exc.code, 'Inspect secret presence and OAuth account configuration; no credential values are logged.')
        code = 1
    print(json.dumps(report, indent=2))
    ca = report.get('channel_access') or {}
    print('::notice title=oauth::' + json.dumps({'refresh_ok': report.get('oauth_refresh_succeeded'),
          'upload_scope': report.get('upload_scope_confirmed'), 'channels': ca.get('channels'),
          'expected_matches': ca.get('expected_channel_matches'), 'error_code': report.get('error_code')}, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
