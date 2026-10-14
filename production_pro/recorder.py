"""Record actual interactions with an original locally served app."""
from __future__ import annotations
import os, subprocess, time
from pathlib import Path
from collections.abc import Callable
from playwright.sync_api import sync_playwright
from .models import RecordedSession, RecordedChapter
from .errors import RecorderError

class WorkflowRecorder:
    def __init__(self, base_url: str, output_dir: Path, viewport=(1280,720), *, initial_wait_ms=650, chapter_pause_ms=700):
        if base_url != 'local-inline-demo' and not base_url.startswith('http://127.0.0.1:'):
            raise RecorderError('Only a loopback local demo is permitted in this prototype')
        self.base_url=base_url; self.output_dir=Path(output_dir); self.viewport=viewport
        if not 0 <= initial_wait_ms <= 5000 or not 0 <= chapter_pause_ms <= 5000:
            raise RecorderError('Recording pauses must be between zero and five seconds')
        self.initial_wait_ms=initial_wait_ms;self.chapter_pause_ms=chapter_pause_ms

    def record(self, steps: list[tuple[str, Callable]]) -> RecordedSession:
        self.output_dir.mkdir(parents=True,exist_ok=True)
        chapters=[]
        with sync_playwright() as pw:
            options={'headless':True,'args':['--no-sandbox']}
            if os.path.isfile('/usr/bin/chromium'):
                options['executable_path']='/usr/bin/chromium'
            browser=pw.chromium.launch(**options)
            try:
                ctx=browser.new_context(viewport=dict(width=self.viewport[0],height=self.viewport[1]),record_video_dir=str(self.output_dir),record_video_size=dict(width=self.viewport[0],height=self.viewport[1]))
                page=ctx.new_page()
                if self.base_url == 'local-inline-demo':
                    site=Path(__file__).parent/'site'
                    html=(site/'index.html').read_text(encoding='utf-8')
                    css=(site/'styles.css').read_text(encoding='utf-8')
                    js=(site/'app.js').read_text(encoding='utf-8')
                    html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+css+'</style>').replace('<script src="app.js"></script>','<script>'+js+'</script>')
                    page.set_content(html,wait_until='domcontentloaded')
                else:
                    page.goto(self.base_url,wait_until='domcontentloaded')
                page.wait_for_timeout(self.initial_wait_ms)
                t0=time.monotonic()
                for name,action in steps:
                    start=time.monotonic()-t0
                    action(page)
                    page.wait_for_timeout(self.chapter_pause_ms)
                    chapters.append(RecordedChapter(name=name,start_s=start,end_s=time.monotonic()-t0))
                raw=Path(page.video.path())
                ctx.close()  # video flushed before querying duration
            finally: browser.close()
        if not raw.exists() or raw.stat().st_size<1000:
            raise RecorderError('Browser failed to record nonempty video')
        proc=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(raw)],capture_output=True,text=True,check=True)
        return RecordedSession(video_path=str(raw),width=self.viewport[0],height=self.viewport[1],duration_s=float(proc.stdout.strip()),chapters=chapters)

def focus_element(page, selector: str):
    """Emphasize a real element in our original demo; never fake app results."""
    page.locator(selector).evaluate('''el => {
        document.querySelectorAll('[data-focused]').forEach(n => n.removeAttribute('data-focused'));
        const panel=el.closest('.panel') || el;
        panel.setAttribute('data-focused','true');
        document.documentElement.dataset.focus = el.id || 'overview';
    }''')
