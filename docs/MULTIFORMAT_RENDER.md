# Animated cloud render

The existing CPU pipeline now creates both 1920×1080 and 1080×1920 versions
of the original functioning expense-rule demo. Real Chromium interactions
follow the synthesized speech timeline. Both manager review ($120 travel)
and automatic approval ($80 travel) are asserted against actual app results.
No business-performance figures or third-party SaaS claims are invented.

`scripts/render_showcase.py` performs actual Piper synthesis, two-pass loudness
normalization, WhisperX CTC alignment, responsive Playwright recording, timed
CSS focus zoom/pan, FFmpeg rendering and word-highlight subtitle animation.
ASS karaoke timings include real gaps between WhisperX words; independent
caption checks remove styling tags before validating complete ordered text.
Portrait captions reserve a 300-pixel bottom margin.

## Cloud operation

- `.github/workflows/ci.yml`: full offline suite, actual browser layout tests,
  OAuth token protection tests and small JUnit artifacts.
- `.github/workflows/render-final.yml`: manual `both`, `landscape` or `portrait`
  render. No API keys are needed for this original demo.
- Both require `ZERO_COST_ACTIONS_CONFIRMED=1`; the account has an existing
  $0 Actions spending budget. No paid provider, GPU, uploaded cache or public
  video upload is activated. Videos/audio/QA are kept for seven days on GitHub.
- Provider drafting still requires approved free account credentials. This
  render does not simulate successful live model research or OAuth consent.

## Optional owner-local OAuth

The current cloud render does not need Google access. Future YouTube account
connection still requires genuine owner consent. When a computer is available:

```bash
python -m scripts.oauth_setup --status
python -m scripts.oauth_setup --client-secrets .secrets/client_secrets.json
```

Use a Google Desktop application client; the browser and callback must share
that computer. Tokens use atomic mode-0600 writes, fsync and symlink refusal.
Token files, client secrets and .secrets are ignored by Git and never included
in render artifacts. The setup flow never uploads a video.

The standalone engine also accepts `channel.cli render --format portrait`.
Existing chart or footage assets must themselves be suitable for the target
aspect ratio; the showcase records the application at the native resolution.
