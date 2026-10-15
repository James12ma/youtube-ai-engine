# OAuth follow-up — 2026-10-15 03:37 UTC

Repository preserved: James12ma/youtube-ai-engine.
Executable revision checked: 3a287e62464e38bca02de9205db7632bd65e82cc.
This follow-up supersedes the earlier report's CURRENT OAuth error classification, not its historical invalid_client observations.

## Evidence
Inspected current channel/oauth.py, scripts/check_cloud_oauth.py, .github/workflows/oauth-check.yml and the installed Google OAuth SDK request logic.
Latest prior runs #9 (38675236802), #10 (38675261672), #11 (38676440976) all failed real refresh with unauthorized_client; all installed dependencies and passed the 11 existing offline OAuth tests.
GitHub secret metadata shows all three required YouTube secret names exist and have been updated. Values were not retrieved, printed, requested, or exported.

Executed exactly one new read-only verification:
https://github.com/James12ma/youtube-ai-engine/actions/runs/38677162176
Run #12, job 116233281600: dependencies PASS; 11 OAuth tests PASS; real token refresh FAIL, unauthorized_client at 03:37:01 UTC.
No access token obtained, so actual channels.list was not reached. Correct YouTube channel access remains unverified.

## Diagnosis and limits
No incorrect environment mapping or token endpoint was found. The implementation uses the Google SDK's refresh-token grant with the three configured secrets and a fixed Google HTTPS token endpoint.
Current Google error rejects the client/grant combination. It does not prove which secret is wrong, whether a token is expired, or that all three belong to the same active client.
Replacing/deleting/recreating a client must not be assumed to transfer the previous refresh grant. A token issued under OAuth Playground's default client also cannot be assumed to belong to the owner's client.
Those possibilities require checking the actual Google client and authorization issuance context, which remain unavailable.

Google Cloud https://console.cloud.google.com/apis/credentials returned Site Unavailable / Unable to access this site, including after one reload. There was no usable login or credential-management surface. No bot block or owner-login diagnosis is inferred from this generic access failure.
The currently available connected Google applications do not expose OAuth client administration; GitHub's connector does not expose secret value readback or a dedicated secret-management action.
Consequently, client type/status, redirect configuration, consent-screen state, token-to-client binding and credential rotation could not be verified or repaired through available secure access.

## Changes and safeguards
No operational code change was justified by the observed failure. No credentials were created, replaced, revoked or deleted, and no safeguards were relaxed.
This commit records the new evidence only; it is not an OAuth repair or readiness claim.
No new credential values entered logs/chat/files/artifacts. No video uploaded or published, no paid API enabled, no money spent.
Next required capability is secure access to the existing Google OAuth client's configuration and owner authorization flow, followed by a matching-credential live check. Do not repeatedly change secrets without verifying their shared issuance context.
