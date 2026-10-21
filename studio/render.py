"""Frame-exact renderer: headless Chromium draws each frame from the runtime, FFmpeg encodes.

The page is offline (all network requests are blocked), so AI-written scene code cannot reach anything.
While rendering, every frame is measured for the QA report: JS errors, blank frames and the longest
stretch without visible change."""
from __future__ import annotations

import io
import json
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

WEB = Path(__file__).with_name('web')


class RenderError(RuntimeError):
    pass


def _thumb(jpeg: bytes) -> np.ndarray:
    im = Image.open(io.BytesIO(jpeg)).convert('L').resize((54, 96))
    return np.asarray(im, dtype=np.float32)


class Stage:
    """A loaded plan in a headless browser. Use as a context manager."""

    def __init__(self, data: dict, *, browser_path: str | None = None):
        self.data = data; self.browser_path = browser_path

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        kw = {'args': ['--disable-gpu', '--font-render-hinting=none', '--disable-lcd-text']}
        if self.browser_path:
            kw['executable_path'] = self.browser_path
        self.browser = self._pw.chromium.launch(**kw)
        w, h = {'horizontal': (1920, 1080), 'square': (1080, 1080)}.get(self.data['format'], (1080, 1920))
        self.w, self.h = w, h
        self.page = self.browser.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
        self.page.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
        self.page.goto((WEB / 'stage.html').resolve().as_uri())
        self.page.evaluate('document.fonts.ready.then(()=>true)')
        info = self.page.evaluate('d=>STUDIO.load(d)', self.data)
        self.page.evaluate("Promise.all([...document.fonts].map(f=>f.load())).then(()=>true)")
        self.load_errors = info.get('errors', [])
        self.cdp = self.page.context.new_cdp_session(self.page)
        return self

    def frame(self, t: float, quality: int = 92) -> bytes:
        self.page.evaluate('t=>STUDIO.render(t)', t)
        import base64
        r = self.cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': quality, 'optimizeForSpeed': True,
                                                     'clip': {'x': 0, 'y': 0, 'width': self.w, 'height': self.h, 'scale': 1}})
        return base64.b64decode(r['data'])

    def errors(self) -> list[str]:
        return self.page.evaluate('STUDIO.errors()')

    def area(self, i: int) -> float:
        return self.page.evaluate('i=>STUDIO.area(i)', i)

    def overflow(self, i: int) -> float:
        return self.page.evaluate('i=>STUDIO.overflow(i)', i)

    def __exit__(self, *exc):
        try:
            self.browser.close()
        finally:
            self._pw.stop()


def render_video(data: dict, out: Path, *, audio: Path | None = None, fps: int = 30,
                 browser_path: str | None = None, preview_every: float = 0.0) -> dict:
    """Render to `out` (MP4). Returns a QA report of what was actually drawn."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(data['duration'] * fps))
    video = out.with_suffix('.video.mp4')
    ff = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg',
                           '-framerate', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                           '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-movflags', '+faststart', str(video)],
                          stdin=subprocess.PIPE)
    diffs, stds, previews = [], [], []
    t0 = time.monotonic(); prev = None
    try:
        with Stage(data, browser_path=browser_path) as st:
            shots = data['shots']; overflow = [0.0] * len(shots)
            for i in range(n):
                jpg = st.frame(i / fps)
                if i % fps == 0:
                    k = max([j for j, s in enumerate(shots) if s['start'] <= i / fps] or [0])
                    overflow[k] = max(overflow[k], round(st.overflow(k), 3))
                ff.stdin.write(jpg)
                th = _thumb(jpg)
                stds.append(float(th.std()))
                diffs.append(0.0 if prev is None else float(np.abs(th - prev).mean()))
                prev = th
                if preview_every and i % int(preview_every * fps) == 0:
                    previews.append((i / fps, jpg))
            errors = st.load_errors + st.errors()
    finally:
        ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise RenderError('ffmpeg encoding failed')
    if audio:
        subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(video), '-i', str(audio),
                        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                        '-shortest', '-movflags', '+faststart', str(out)], check=True)
        video.unlink()
    else:
        video.replace(out)
    # longest stretch without visible change (seconds)
    run = best = 0
    for d in diffs[1:]:
        run = run + 1 if d < 0.6 else 0
        best = max(best, run)
    report = {'frames': n, 'fps': fps, 'seconds': round(n / fps, 2), 'render_seconds': round(time.monotonic() - t0, 1),
              'js_errors': errors[:20], 'blank_frames': int(sum(s < 2.0 for s in stds)),
              'longest_static_s': round(best / fps, 2), 'shot_overflow': overflow}
    for t, jpg in previews:
        (out.parent / f'preview_{t:06.2f}.jpg').write_bytes(jpg)
    return report


def snapshot(data: dict, times: list[float], out_dir: Path, *, browser_path: str | None = None) -> dict:
    """Render a few frames only (fast checks of a plan or of AI-written scene code)."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    shots = data['shots']
    area, overflow = [0.0] * len(shots), [0.0] * len(shots)
    with Stage(data, browser_path=browser_path) as st:
        thumbs, files = [], []
        for t in times:
            jpg = st.frame(t); p = out_dir / f'frame_{t:07.3f}.jpg'; p.write_bytes(jpg); files.append(p)
            thumbs.append(_thumb(jpg))
            i = max([k for k, s in enumerate(shots) if s['start'] <= t] or [0])
            area[i] = max(area[i], round(st.area(i), 4)); overflow[i] = max(overflow[i], round(st.overflow(i), 3))
        errors = st.load_errors + st.errors()
    changes = [float(np.abs(a - b).mean()) for a, b in zip(thumbs, thumbs[1:])]
    return {'files': [str(f) for f in files], 'js_errors': errors, 'blank': [float(t.std()) < 2.0 for t in thumbs],
            'changes': changes, 'shot_overflow': overflow, 'shot_area': area}


if __name__ == '__main__':
    import sys
    d = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(render_video(d, Path(sys.argv[2])), indent=2))
