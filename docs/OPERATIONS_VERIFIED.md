# Operational verification — 2026-10-14

The original source architecture is preserved. Local CPU narration and video
rendering are validated. This is not a live deployed autonomous channel.

## Reproduce the tested environment

Use Python 3.12, Git, FFmpeg with libass, and an isolated virtual environment.
The verification artifact contains the actual installed dependency snapshots.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-production.txt -r requirements-production-pro.txt -r requirements-release.txt
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python -m compileall -q state_store.py adapters router pipeline verification production production_pro narration_pro channel scripts tests
.venv/bin/python -m pytest -q -rs
```

For the optional real neural stack:

```bash
python -m venv .venv-narration
.venv-narration/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 torchaudio==2.8.0 torchvision==0.23.0
.venv-narration/bin/python -m pip install -r requirements-narration.txt -r requirements.txt -r requirements-production-pro.txt
.venv-narration/bin/python -m pip check
.venv-narration/bin/python -m piper.download_voices --data-dir voices en_US-libritts-high
.venv-narration/bin/python -c "import nltk; nltk.download('punkt_tab', raise_on_error=True)"
.venv-narration/bin/python -m scripts.narration_smoke --voice voices/en_US-libritts-high.onnx --transcript 'This is an original local demonstration of expense approval rules.' --output-dir outputs/neural-smoke
.venv-narration/bin/python -m scripts.enforce_gates --out-dir outputs/neural-smoke
```

The local verification used Playwright 1.56.0 after the current 1.64.0 browser
download failed in this environment. Chromium 141 recorded real DOM interactions.
This download workaround is environment-specific; it is not evidence that
1.64.0 is defective generally. A fixed official NLTK tokenizer archive was
downloaded and safely extracted locally because the NLTK downloader refused
the environment's proxy. No global proxy safety switch was disabled.

To reproduce the original browser demo with neural voice, run
`run_task7_demo.py --piper-model voices/en_US-libritts-high.onnx --size 1920x1080`,
then `python -m scripts.align_demo`. The first demo's captions are approximate;
the second output uses actual WhisperX CTC alignment. The additional
`python -m scripts.channel_render_demo` exercises the assembled channel
renderer against a clearly labelled local engineering verification fixture,
after creating `outputs/browser-demo/recording.json` with WorkflowRecorder.
It does not claim successful live research or model-based fact checking.

## GitHub and budget

- A local `main` repository is prepared; no external repository was created.
- No GitHub Actions job was dispatched and no account billing quota was readable.
- All workflows require `ZERO_COST_ACTIONS_CONFIRMED=1` before running. Set it
  only after confirming included minutes/storage and a spending limit that
  prevents paid overages in the account. The variable is an acknowledgement,
  not an automatic quota meter or billing cap.
- Draft workflows additionally require `FREE_PROVIDER_ACCOUNTS_CONFIRMED=1`.
- `ENABLE_AUTOMATION` is unset and the supplied queue remains disabled.
- No paid API, GPU, hosting service or video upload was activated.
- Live AI requests remain off until approved free provider credentials and
  account billing limits are available. Model-name allowlists alone cannot
  establish a provider account's billing status.

## OAuth setup on the owner's computer

Use the Google Desktop application client with the YouTube Data API enabled.
The browser and localhost callback must run on the same owner's computer.
Phone-only completion of this callback has not been implemented or tested.

```bash
python -m pip install -r requirements-release.txt
python -m channel.cli oauth-authorize --client-secrets .secrets/client_secrets.json --token-file .secrets/youtube-token.json
python -m channel.cli oauth-status --token-file .secrets/youtube-token.json
```

The setup writes an atomic mode-0600 token and never uploads a video. Actual
Google consent is still pending. OAuth URL construction and YouTube SDK
initialization were tested with dummy credentials and no external API calls.
An expired access token still requires owner-controlled refresh/reauthorization
before the existing uploader will proceed. For reauthorization, preserve the
old token securely outside the configured path before rerunning consent.

The package command now accepts `--contains-synthetic-media yes|no`, so the
owner's disclosure decision can be included before immutable approval hashes
are generated. Never modify an approved release to change metadata.

## Content and approval

No owner approval was recorded for any demo. No release was marked ready for
publication. Before using any narration commercially, inspect/listen to it,
check pronunciation and visual timing, and review model/output terms. The
LibriTTS high model card identifies its training dataset as CC BY 4.0; this
does not establish every component's commercial-use terms by itself.

Primary references:

- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
- https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts/high/MODEL_CARD
- https://github.com/m-bain/whisperX/releases/tag/v3.8.6
- https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html
