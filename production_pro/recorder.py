"""Record actual interactions with an original locally served app."""
from __future__ import annotations
import os, subprocess, time
from pathlib import Path
from collections.abc import Callable
from playwright.sync_api import sync_playwright
from .models import RecordedSession, RecordedChapter
from .errors import RecorderError

class WorkflowRecorder:
    def __init__(self, base_url: str, output_dir: Path, viewport=(1280,720)):
        if base_url != 'local-inline-demo' and not base_url.startswith('http://127.0.0.1:'):
            raise RecorderError('Only a loopback local demo is permitted in this prototype')
        self.base_url=base_url; self.output_dir=Path(output_dir); self.viewport=viewport

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
                page.wait_for_timeout(650)
                t0=time.monotonic()
                for name,action in steps:
                    start=time.monotonic()-t0
                    action(page)
                    page.wait_for_timeout(700)
                    chapters.append(RecordedChapter(name=name,start_s=start,end_s=time.monotonic()-t0))
                raw=Path(page.video.path())
                ctx.close()  # video flushed before querying duration
            finally: browser.close()
        if not raw.exists() or raw.stat().st_size<1000:
            raise RecorderError('Browser failed to record nonempty video')
        proc=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(raw)],capture_output=True,text=True,check=True)
        return RecordedSession(video_path=str(raw),width=self.viewport[0],height=self.viewport[1],duration_s=float(proc.stdout.strip()),chapters=chapters)
