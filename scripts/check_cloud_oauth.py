"""Refresh owner OAuth in cloud, print only readiness booleans. Never uploads."""
import json
import os
from channel.oauth import load_upload_credentials, OAuthConfigurationError, UPLOAD_SCOPE


def main():
    report = {'uploads_enabled': False, 'publications_enabled': False,
              'live_llm_calls': 0,
              'provider_key_present': {name: bool(os.environ.get(name)) for name in
                  ('GROQ_API_KEY', 'GEMINI_API_KEY', 'OPENROUTER_API_KEY')}}
    try:
        credentials = load_upload_credentials()
        report.update(oauth_refresh_succeeded=True, access_token_valid=credentials.valid,
                      upload_scope_requested=True,
                      upload_scope_confirmed=(UPLOAD_SCOPE in credentials.granted_scopes)
                          if credentials.granted_scopes is not None else None)
        code = 0
    except OAuthConfigurationError as exc:
        report.update(oauth_refresh_succeeded=False, error=str(exc))
        code = 1
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
