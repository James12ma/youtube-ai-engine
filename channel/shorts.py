"""Vertical Shorts cut from a finished long video, to send viewers to it.

Each Short is a continuous, sentence-aligned excerpt of the long video's own
narration (no new claims), reframed to 1080x1920 with large word-timed
captions. Nothing is uploaded here.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Sequence
from pydantic import BaseModel
from narration_pro.aligner import WordTimestamp
from narration_pro.captions import build_ass_from_words

SENTENCE_END = ('.', '?', '!', '…')
MIN_SHORT_S = 20.0
MAX_SHORT_S = 58.0  # stay under one minute: works on every Shorts surface


class ShortsError(RuntimeError):
    pass


class ShortPlan(BaseModel):
    index: int
    chapter_title: str
    start_s: float
    end_s: float
    words: int

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        raise ShortsError('FFmpeg error: ' + proc.stderr[-700:])


def plan_shorts(words: Sequence[WordTimestamp], chapters: Sequence[dict], *, count: int = 3,
                min_s: float = MIN_SHORT_S, max_s: float = MAX_SHORT_S) -> list[ShortPlan]:
    """Pick up to ``count`` excerpts, each starting at a chapter and ending on a sentence.

    The introduction (first chapter) is skipped when other chapters exist, so a
    Short opens on substance. Chapters are taken in order of their position,
    spread across the video.
    """
    if not words:
        raise ShortsError('no aligned words')
    starts = sorted(((float(c['start_s']), str(c['title'])) for c in chapters), key=lambda c: c[0])
    if len(starts) > 1:
        starts = starts[1:]
    candidates: list[ShortPlan] = []
    for start_s, title in starts:
        first = next((i for i, w in enumerate(words) if w.start_s >= start_s - 0.05), None)
        if first is None:
            continue
        begin = words[first].start_s
        best = None
        for j in range(first, len(words)):
            if words[j].end_s - begin > max_s:
                break
            if words[j].word.rstrip('"\')»”').endswith(SENTENCE_END) and words[j].end_s - begin >= min_s:
                best = j
        if best is None:
            continue
        candidates.append(ShortPlan(index=0, chapter_title=title, start_s=round(begin, 3),
                                    end_s=round(words[best].end_s + 0.25, 3), words=best - first + 1))
    if not candidates:
        return []
    if len(candidates) > count:
        step = len(candidates) / count
        candidates = [candidates[int(i * step)] for i in range(count)]
    return [c.model_copy(update={'index': i}) for i, c in enumerate(candidates)]


def _dimensions(path: Path) -> tuple[int, int]:
    proc = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                           '-of', 'csv=p=0:s=x', str(path)], capture_output=True, text=True)
    try:
        w, h = proc.stdout.strip().split('x')[:2]
        return int(w), int(h)
    except ValueError:
        return 16, 9


def cut_short(source_video: Path, words: Sequence[WordTimestamp], plan: ShortPlan, output: Path,
              *, width: int = 1080, height: int = 1920) -> dict:
    """Reframe one excerpt of the UNCAPTIONED long video to vertical with new captions."""
    source_video = Path(source_video)
    if not source_video.is_file():
        raise ShortsError('source video missing')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / (output.stem + '_work')
    work.mkdir(parents=True, exist_ok=True)
    shifted = [WordTimestamp(word=w.word, start_s=max(0.0, w.start_s - plan.start_s),
                             end_s=w.end_s - plan.start_s, score=w.score)
               for w in words if w.start_s >= plan.start_s - 0.01 and w.end_s <= plan.end_s + 0.01]
    if not shifted:
        raise ShortsError('no words inside the excerpt')
    ass = work / 'captions.ass'
    build_ass_from_words(shifted, ass, width=width, height=height, animated=True, size=78,
                         max_chars_per_line=18, bottom_margin=430, max_duration_s=2.0)
    sub = str(ass.resolve()).replace('\\', '\\\\').replace(':', '\\:').replace("'", r"\'") \
        .replace('[', r'\[').replace(']', r'\]')
    src_w, src_h = _dimensions(source_video)
    if src_h > src_w:
        # Native vertical render: scenes were drawn for 9:16, just add captions.
        graph = f'[0:v]scale={width}:{height},subtitles=filename=\'{sub}\'[v]'
    else:
        # Fallback for a landscape source: blurred full-bleed background + the
        # original 16:9 frame centred above captions (small text gets hard to read).
        graph = (f'[0:v]split=2[bg][fg];'
                 f'[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=24:2[b];'
                 f'[fg]scale={width}:-2[f];'
                 f'[b][f]overlay=(W-w)/2:(H-h)/2-260,subtitles=filename=\'{sub}\'[v]')
    _run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
          '-ss', f'{plan.start_s:.3f}', '-t', f'{plan.duration_s:.3f}', '-i', str(source_video),
          '-filter_complex', graph, '-map', '[v]', '-map', '0:a:0',
          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p',
          '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(output)])
    return {'output': str(output), 'start_s': plan.start_s, 'end_s': plan.end_s,
            'duration_s': round(plan.duration_s, 3), 'chapter': plan.chapter_title,
            'width': width, 'height': height, 'captions': str(ass)}


def make_shorts(render_work_dir: Path, out_dir: Path, *, count: int = 3) -> list[dict]:
    """Shorts from a render work directory (uncaptioned.mp4, words.json, render_report.json)."""
    work = Path(render_work_dir)
    report = json.loads((work / 'render_report.json').read_text(encoding='utf-8'))
    aligned = json.loads((work / 'words.json').read_text(encoding='utf-8'))
    words = [WordTimestamp.model_validate(w) for w in aligned['words']]
    plans = plan_shorts(words, report.get('chapters') or [], count=count)
    if not plans:
        raise ShortsError('no sentence-aligned excerpt between %.0f and %.0f seconds' % (MIN_SHORT_S, MAX_SHORT_S))
    results = [cut_short(work / 'uncaptioned.mp4', words, p, Path(out_dir) / f'short_{p.index + 1}.mp4')
               for p in plans]
    (Path(out_dir) / 'shorts_report.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    return results


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Cut vertical Shorts from a finished render (no upload)')
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--count', type=int, default=3)
    args = ap.parse_args()
    print(json.dumps(make_shorts(args.work, args.out, count=args.count), indent=2))
