"""Owner-interactive OAuth setup. No YouTube upload or automatic login."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

UPLOAD_SCOPE = 'https://www.googleapis.com/auth/youtube.upload'
TOKEN_URI = 'https://oauth2.googleapis.com/token'
SECRET_NAMES = ('YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN')


class OAuthConfigurationError(RuntimeError):
    """Sanitized credential error safe for cloud logs."""


def load_upload_credentials(token_file=None, *, environment=None,
                            credentials_factory=None, request_factory=None):
    """Load owner credentials and refresh when needed. Never uploads or prints secrets.

    Existing owner-local token files take precedence over the three cloud secrets.
    Requests go only to Google's fixed token endpoint, with a finite timeout.
    """
    env = os.environ if environment is None else environment
    try:
        if credentials_factory is None:
            from google.oauth2.credentials import Credentials
            credentials_factory = Credentials
        if token_file:
            path = Path(token_file)
            if not path.is_file() or path.is_symlink():
                raise OAuthConfigurationError('OAuth token file unavailable or symbolic link')
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('token_uri', TOKEN_URI) != TOKEN_URI:
                raise OAuthConfigurationError('OAuth token endpoint must be Google')
            credentials = credentials_factory.from_authorized_user_info(data, scopes=[UPLOAD_SCOPE])
        else:
            if not all(env.get(name, '').strip() for name in SECRET_NAMES):
                raise OAuthConfigurationError('Three YouTube OAuth secrets are required')
            credentials = credentials_factory(token=None,
                client_id=env[SECRET_NAMES[0]].strip(), client_secret=env[SECRET_NAMES[1]].strip(),
                refresh_token=env[SECRET_NAMES[2]].strip(), token_uri=TOKEN_URI,
                scopes=[UPLOAD_SCOPE])
        if not credentials.valid:
            if request_factory is None:
                from google.auth.transport.requests import Request
                request_factory = Request
            transport = request_factory()
            def bounded_request(*args, **kwargs):
                kwargs['timeout'] = 30
                return transport(*args, **kwargs)
            credentials.refresh(bounded_request)
        if not credentials.valid:
            raise OAuthConfigurationError('OAuth did not provide a valid access token')
        granted = credentials.granted_scopes
        if granted is not None and UPLOAD_SCOPE not in granted:
            raise OAuthConfigurationError('YouTube upload scope was not granted')
        if token_file:
            save_credentials(credentials, Path(token_file))
        return credentials
    except OAuthConfigurationError:
        raise
    except Exception as exc:
        # Only a fixed OAuth error-code allowlist may enter logs, never error descriptions.
        safe_codes = {'invalid_client', 'invalid_grant', 'invalid_scope',
                      'unauthorized_client', 'access_denied', 'temporarily_unavailable'}
        for item in exc.args:
            if isinstance(item, dict) and item.get('error') in safe_codes:
                raise OAuthConfigurationError('OAuth token request failed: ' + item['error']) from None
        raise OAuthConfigurationError('OAuth validation failed; check credentials and consent') from None


def save_credentials(credentials, path: Path) -> None:
    """Atomic owner-only token file; never echo credentials into logs."""
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('OAuth token destination must not be a symbolic link')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.oauth-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(credentials.to_json())
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def authorize(client_secrets: Path, token_file: Path, *, flow_factory=None) -> dict:
    """Run on the owner's computer, where browser and callback share localhost."""
    if Path(token_file).exists():
        raise ValueError('Token already exists; inspect oauth-status before replacing it')
    config = json.loads(Path(client_secrets).read_text(encoding='utf-8'))
    if 'installed' not in config:
        raise ValueError('Use a Google Desktop app OAuth client')
    if flow_factory is None:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow_factory = InstalledAppFlow.from_client_secrets_file
    flow = flow_factory(str(client_secrets), scopes=[UPLOAD_SCOPE])
    credentials = flow.run_local_server(host='localhost', port=0,
        open_browser=True, timeout_seconds=300,
        authorization_prompt_message='Authorize the YouTube application in your local browser.',
        success_message='Authorization saved. No video has been uploaded.')
    if not credentials.has_scopes([UPLOAD_SCOPE]):
        raise ValueError('Required YouTube upload scope was not granted')
    save_credentials(credentials, token_file)
    return {'authorized': True, 'uploads_enabled': False}


def oauth_status(token_file: Path) -> dict:
    """Local SDK validation only: no refresh, API request or secret output."""
    if not Path(token_file).is_file():
        return {'configured': False, 'uploads_enabled': False}
    from google.oauth2.credentials import Credentials
    credentials = Credentials.from_authorized_user_file(str(token_file))
    return {'configured': True, 'valid': credentials.valid,
            'expired': credentials.expired,
            'has_upload_scope': credentials.has_scopes([UPLOAD_SCOPE]),
            'can_refresh': bool(credentials.refresh_token),
            'uploads_enabled': False}
