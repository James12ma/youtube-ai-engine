# Phone-authorized cloud OAuth

The owner can obtain OAuth consent in Google's OAuth Playground with their own
web client and add three repository Secrets: YOUTUBE_CLIENT_ID,
YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN. No credential values are committed.

`channel.oauth.load_upload_credentials` reads these only when no owner-local
token path was supplied. It refreshes through Google's fixed token endpoint,
uses a 30-second HTTP timeout and sanitizes provider errors. Existing local
files remain supported and are saved atomically with mode 0600 after validation.

The uploader still requires a verified release, actual owner approval, the exact
independently supplied digest and upload environment gate. Public/unlisted
uploads need the additional public gate. None of these gates is enabled by setup.

Run the manual **YouTube OAuth check (no upload)** workflow on a zero-cost
confirmed account. It runs nine offline credential tests, then refreshes the
real owner token and prints only readiness booleans. Tokens are never written
to that workflow's artifacts, logs or outputs. No YouTube upload/API mutation
or LLM request is made. Successful refresh validates the OAuth credentials;
it is not proof that a YouTube upload or correct-channel selection was tested.

Granted scope is checked when Google returns it. If omitted, the report uses
null for scope confirmation rather than inventing proof from requested scope.

Google external apps in Testing can have refresh tokens expire after seven
days. Revoke and replace any token exposed in screenshots before production.
The workflow does not determine whether a stored token has been rotated.

Provider secret presence alone does not establish free-tier account settings;
live AI calls remain behind their existing independent free-account gate.
