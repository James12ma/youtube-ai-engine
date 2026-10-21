# LogicScript Studio — prompt → directed, rendered, checked video

One engine for every video. You give a prompt (or an exact script, or a plan); the Studio writes, directs,
voices, renders and checks the video, then sends it to you. Nothing is published without your approval.

```
prompt ──► Director (free LLMs) ──► plan.json ──► checks ──► Kokoro voice ──► frame-exact render ──► QA ──► MP4
             │  script, beats            │  timing: every cue is a spoken phrase
             │  shots + cues per beat    │  coverage: nothing static > style.max_static_s
             └── repair loop ◄───────────┘  real render: JS errors, empty / static / overflowing shots
```

## Why it can make any style
- **Style is data** (`studio/styles.py`): palette, background, captions (box / karaoke / none), headlines, pacing, music.
  Six packs ship (`explainer-dark`, `explainer-light`, `data-minimal`, `ai-dark`, `screen-demo`, `storybook`);
  the Director can derive new ones.
- **Scenes are code.** Built-in scenes (`studio/web/scenes.js`: characters, phone apps, transfers, inboxes,
  software windows with a mouse, tables, charts, numbers, steps, icons, comparisons, questions, titles) are only
  building blocks. When none fits, the Director writes a `custom` scene in JavaScript against the same API
  (`studio/catalog.py` documents it). Every scene is test-rendered before the real render; errors go back to the
  model for repair.
- **Formats:** vertical 1080×1920, horizontal 1920×1080, square 1080×1080. **Languages:** any Kokoro language.

## Every narration detail is shown
Cues tie visual actions to phrases of the narration ("she *presses* send" → the button is pressed exactly when
"presses" is spoken). The plan is rejected if a phrase is not really spoken in its beat, or if any part of a
beat has nothing new on screen for longer than the style allows.

## Run
```bash
python -m studio.make --prompt "Explain what happens after you apply for a job" --out out/job
python -m studio.make --script-file script.txt --style ai-dark --format horizontal --out out/x
python -m studio.make --plan studio/examples/job_application.json --out out/demo --draft   # silent preview
```
On GitHub: push `studio/jobs/request.json` to a `studio/run-*` branch; `.github/workflows/studio.yml` produces
every job, sends each MP4 to the owner on Telegram and stores an encrypted review pack.

## Limits (honest)
- Realistic cinematic footage (real people, 3D worlds) needs a GPU video model; not available for free on CPU.
  The plan format has room for a `footage` provider later (e.g. Kaggle free GPU) with owner approval.
- Free LLM tiers are rate-limited; the Director retries other free models and never falls back to paid ones.
- Checks are technical (timing, coverage, rendering, audio). Editorial approval remains the owner's.
