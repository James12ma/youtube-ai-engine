"""Render a LogicScript "What's new" video: real official web pages, recorded live, under the narration.

For each segment of plan.json (scripts/whats_new_plan.py): open the official page in Chromium,
clear cookie banners, find the segment's verified quote on the page, highlight it, scroll it into
view and record exactly as long as the narration of that segment. Labels on screen name the source
domain. Narration WAVs come from the shared narrator (scripts/narrate_texts.py, owner-approved voice).
Captions are force-aligned (WhisperX). Nothing is uploaded.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import time
import wave
from pathlib import Path
from urllib.parse import urlparse

W, H, FPS = 1920, 1080, 30
PAUSE = 0.7
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

CLEANUP_JS = """
() => {
  const words = /(accept|agree|got it|allow all|ok|close|dismiss)/i;
  for (const b of document.querySelectorAll('button, [role=button], a')) {
    const t = (b.innerText || '').trim();
    if (t.length < 25 && words.test(t)) { const r = b.getBoundingClientRect();
      const fixed = getComputedStyle(b.closest('[class],[id]') || b).position;
      if (r.width && (fixed === 'fixed' || fixed === 'sticky' || /cookie|consent/i.test(b.outerHTML))) b.click(); }
  }
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if ((s.position === 'fixed' || s.position === 'sticky') && /cookie|consent|banner|chat|intercom|toast/i.test(el.id + ' ' + el.className)) el.remove();
  }
}"""

HIGHLIGHT_JS = """
(quote) => {
  const norm = s => s.normalize('NFKC').replace(/[\\u2018\\u2019]/g, "'").replace(/[\\u201c\\u201d]/g, '"').replace(/\\s+/g, ' ').toLowerCase();
  const q = norm(quote).slice(0, 60);
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let best = null;
  while (walker.nextNode()) {
    const el = walker.currentNode;
    if (!el.offsetParent) continue;
    const t = norm(el.innerText || '');
    if (t.includes(q) && (!best || t.length < norm(best.innerText).length)) best = el;
  }
  if (!best) return false;
  best.style.background = 'rgba(255, 214, 64, 0.55)';
  best.style.boxShadow = '0 0 0 6px rgba(255, 214, 64, 0.55)';
  best.style.borderRadius = '6px';
  best.scrollIntoView({behavior: 'smooth', block: 'center'});
  return true;
}"""


def run(cmd):
    subprocess.run(cmd, check=True)


def wav_seconds(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def esc(t: str) -> str:
    return t.replace('\\', '\\\\').replace(':', '\\:').replace("'", '’').replace('%', '\\%')


def record_segments(plan: dict, durations: list[float], work: Path) -> list[dict]:
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i, (seg, d) in enumerate(zip(plan['segments'], durations)):
            vdir = work / f'rec_{i:02d}'
            vdir.mkdir(parents=True, exist_ok=True)
            # a 1280x720 page recorded at 1280x720 and scaled to 1920x1080 = text 1.5x larger, readable on a phone
            # (recording at a size larger than the viewport leaves the page in a corner on a grey canvas)
            ctx = b.new_context(viewport={'width': 1280, 'height': 720}, record_video_dir=str(vdir),
                                record_video_size={'width': 1280, 'height': 720}, locale='en-US', device_scale_factor=1)
            t0 = time.time()
            page = ctx.new_page()
            ok, err = False, ''
            try:
                page.goto(seg['url'], wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(3500)
                page.evaluate(CLEANUP_JS)
                page.wait_for_timeout(800)
                for q in seg.get('valid_quotes') or seg['quotes']:
                    if page.evaluate(HIGHLIGHT_JS, q):
                        ok = True
                        break
                page.wait_for_timeout(1500)          # smooth scroll settles
                t_ready = time.time() - t0
                steps = max(1, int(d))
                px = max(1, min(12, 160 // steps))   # slow drift, at most ~160 px so the highlight stays on screen
                for _ in range(steps):
                    page.mouse.wheel(0, px)
                    page.wait_for_timeout(1000)
                page.wait_for_timeout(600)
            except Exception as exc:
                err = f'{type(exc).__name__}: {str(exc)[:160]}'
                t_ready = time.time() - t0
            page.close()
            ctx.close()
            webm = next(vdir.glob('*.webm'))
            clip = work / f'seg_{i:02d}.mp4'
            label = f"{i + 1}/{len(plan['segments'])} · {seg['title']}"
            src = 'Source: ' + (urlparse(seg['url']).hostname or '')
            vf = (f"fps={FPS},scale={W}:{H}:flags=lanczos,"
                  f"drawbox=x=0:y=0:w=iw:h=86:color=black@0.62:t=fill,"
                  f"drawtext=fontfile={FONT_B}:text='{esc(label)}':x=40:y=24:fontsize=38:fontcolor=white,"
                  f"drawtext=fontfile={FONT}:text='{esc(src)}':x=w-tw-40:y=30:fontsize=30:fontcolor=0xFFD640")
            run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{max(0.0, t_ready - 0.2):.2f}', '-i', str(webm),
                 '-t', f'{d:.3f}', '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', str(clip)])
            got = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(clip)],
                                       capture_output=True, text=True).stdout or 0)
            if got < d - 0.25:   # recording shorter than the narration: pad by holding the LAST frame briefly (logged)
                pad = work / f'seg_{i:02d}_pad.mp4'
                run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(clip), '-vf', f'tpad=stop_mode=clone:stop_duration={d - got:.3f}',
                     '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', str(pad)])
                pad.replace(clip)
            out.append({'segment': i, 'url': seg['url'], 'quote_highlighted': ok, 'error': err, 'seconds': round(d, 2),
                        'recorded_s': round(got, 2), 'padded_s': round(max(0.0, d - got), 2)})
        b.close()
    return out


def card(text_lines: list[tuple[str, int, str]], seconds: float, out: Path) -> None:
    vf = ','.join(f"drawtext=fontfile={FONT_B if big >= 60 else FONT}:text='{esc(t)}':x=(w-tw)/2:y={y}:fontsize={big}:fontcolor={c}"
                  for (t, big, c), y in zip(text_lines, range(380, 1000, 120)))
    run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c=0x0b1220:s={W}x{H}:r={FPS}:d={seconds}',
         '-vf', vf, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--narration-dir', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    from narration_pro import WhisperXAligner, normalize_loudness, build_ass_from_words, save_srt_from_blocks
    from production_pro.editing import burn_captions
    from channel.ai_sources import AI_SOURCES
    plan = json.loads(a.plan.read_text(encoding='utf-8'))
    man = json.loads((a.narration_dir / 'manifest.json').read_text(encoding='utf-8'))
    work = (a.out.parent / (a.out.stem + '_work')).resolve()   # absolute: ffmpeg concat resolves paths from the list's folder
    work.mkdir(parents=True, exist_ok=True)
    wavs = [a.narration_dir / b['file'] for b in man['beats']]
    if len(wavs) != len(plan['segments']):
        raise SystemExit('narration and plan do not match')
    durs = [wav_seconds(w) + PAUSE for w in wavs]
    rec = record_segments(plan, durs, work)
    company = AI_SOURCES[plan['ai']]['company']
    end = work / 'end.mp4'
    card([("Sources: official pages linked in the description", 46, 'white'),
          (f"LogicScript is not affiliated with {company}.", 34, '0xBBBBBB'),
          ("Narration: synthetic AI voice.", 34, '0xBBBBBB')], 5.0, end)
    lst = work / 'list.txt'
    lst.write_text(''.join(f"file '{work / f'seg_{i:02d}.mp4'}'\n" for i in range(len(durs))) + f"file '{end}'\n")
    picture = work / 'picture.mp4'
    run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(picture)])
    # voice: each segment WAV followed by its pause, then silence under the end card
    vin, filt = [], []
    for i, w in enumerate(wavs):
        vin += ['-i', str(w)]
        filt.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=mono,apad=pad_dur={PAUSE}[a{i}]')
    filt.append(''.join(f'[a{i}]' for i in range(len(wavs))) + f'concat=n={len(wavs)}:v=0:a=1,apad=pad_dur=5[v]')
    raw = work / 'voice_raw.wav'
    run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *vin, '-filter_complex', ';'.join(filt), '-map', '[v]', '-ar', '48000', '-ac', '1', str(raw)])
    voice = work / 'voice.wav'
    normalize_loudness(raw, voice)
    transcript = ' '.join(s['narration'] for s in plan['segments'])
    aligned = WhisperXAligner(language='en', device='cpu', min_token_coverage=.98).align(voice, transcript)
    ass = work / 'captions.ass'
    count, blocks = build_ass_from_words(aligned.words, ass, width=W, height=H, size=56, max_chars_per_line=38,
                                         bottom_margin=60, max_duration_s=3.2)
    save_srt_from_blocks(blocks, a.out.with_suffix('.srt'))
    muxed = work / 'muxed.mp4'
    run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(picture), '-i', str(voice), '-map', '0:v', '-map', '1:a',
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(muxed)])
    burn_captions(muxed, ass, a.out)
    # chapters from segment starts
    t, chapters = 0.0, []
    for s, d in zip(plan['segments'], durs):
        chapters.append(f"{int(t // 60)}:{int(t % 60):02d} {s['title']}")
        t += d
    report = {'segments': rec, 'captions': count, 'chapters': chapters,
              'quotes_highlighted': sum(r['quote_highlighted'] for r in rec), 'padded_total_s': round(sum(r['padded_s'] for r in rec), 2),
              'sources': sorted({s['url'] for s in plan['segments']})}
    (work / 'render_report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('captions', 'quotes_highlighted', 'padded_total_s')}))


if __name__ == '__main__':
    main()
