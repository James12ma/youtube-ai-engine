"""Owner-interactive OAuth setup. No YouTube upload or automatic login."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

UPLOAD_SCOPE = 'https://www.googleapis.com/auth/youtube.upload'


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
