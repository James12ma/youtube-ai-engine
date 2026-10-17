"""Visual QA for Alan7 documentaries: is the animal on screen, how close, under water, and is the edit varied?

The "visual standard" (owner, Oct 2026): close shots of the animals first,
especially under water; few empty-sea or landscape shots; every shot must show
what the narration talks about; open on a shot that creates curiosity.

How it measures (free, CPU, open models, nothing leaves the runner):
- CLIP (openai/clip-vit-large-patch14, calibrated) zero-shot on one frame per second:
  scene = underwater / surface / land / card, and "is the subject in frame".
- OWL-ViT (google/owlvit-base-patch32) open-vocabulary boxes for the subject:
  the biggest box's share of the frame gives close / medium / far.
- Shot list from the render report: shot lengths, distinct clips, shot types,
  and for each shot whether the expected subject (Shot.expect) is visible.

The numbers are estimates from models, so the report also writes an annotated
frame sheet: a person can see at a glance what the models decided.
"""
from __future__ import annotations
import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

# Pass/fail targets of the new standard. A plan may override them with "visual_targets".
VISUAL_STANDARD = {
    'subject_visible_min': 0.80,      # share of footage seconds where the animal is in frame
    'close_or_medium_min': 0.55,      # share of footage seconds where the animal is big enough to "be there"
    'underwater_min': 0.40,           # share of footage seconds filmed under water (marine episodes)
    'empty_max': 0.10,                # empty sea / landscape without the animal
    'max_shot_s': 8.0,                # no single shot longer than this
    'mean_shot_s_max': 5.5,
    'shot_types_min': 4,              # distinct shot types (scene x distance)
    'same_type_run_max': 4,           # consecutive shots of the same type
    'narration_match_min': 0.90,      # shots whose expected subject is actually visible
    'hook_subject_min': 0.75,         # first 5 s: animal visible ...
    'hook_close_or_underwater': True,  # ... and either close or under water
}

# Calibrated Oct 2026 on hand-labelled NOAA footage (scripts/visual_calibrate.py, 202 frames):
# CLIP ViT-L/14 + these prompts + max-per-group = 87 % scene accuracy (underwater recall 96 %);
# the main remaining error is beaches read as "surface". ViT-B/16 reached only 69 %.
SCENES = {
    'underwater': ['an underwater photo in the ocean', 'an underwater photo of a coral reef',
                   'an underwater photo of a large animal swimming in blue water'],
    'surface': ['a photo of the ocean surface', 'an aerial drone photo of the sea from above',
                'a photo of an animal at the surface of the sea seen from a boat'],
    'land': ['a photo of a sandy beach', 'a photo of a rocky coastline', 'a photo of snowy mountains and icebergs',
             'a photo of a forest or green hills', 'an aerial photo of an island'],
    'card': ['white text on a plain black background'],
}
EMPTY_PROMPTS = ['a photo of empty sea water with no animals', 'a landscape photo with no animals',
                 'white text on a plain black background']
CLOSE_AREA, MEDIUM_AREA = 0.12, 0.025
BOX_MIN_SCORE = 0.12


class Scorer(Protocol):
    def __call__(self, images: list, subjects: list[str]) -> list[dict]: ...


def closeness(area: float, present: bool) -> str:
    if area >= CLOSE_AREA:
        return 'close'
    if area >= MEDIUM_AREA:
        return 'medium'
    return 'far' if present or area > 0 else 'none'


class ModelScorer:
    """CLIP + OWL-ViT on CPU. Loaded once; ~0.8 s per frame on a GitHub runner."""

    def __init__(self, clip_id: str = 'openai/clip-vit-large-patch14', owl_id: str = 'google/owlvit-base-patch32'):
        import torch
        from transformers import CLIPModel, CLIPProcessor, OwlViTForObjectDetection, OwlViTProcessor
        self.torch = torch
        torch.set_grad_enabled(False)
        self.clip = CLIPModel.from_pretrained(clip_id).eval()
        self.clip_proc = CLIPProcessor.from_pretrained(clip_id)
        self.owl = OwlViTForObjectDetection.from_pretrained(owl_id).eval()
        self.owl_proc = OwlViTProcessor.from_pretrained(owl_id)
        self.models = {'clip': clip_id, 'detector': owl_id}

    def _clip_probs(self, images, prompts):
        inp = self.clip_proc(text=prompts, images=images, return_tensors='pt', padding=True)
        return self.clip(**inp).logits_per_image.softmax(dim=-1)

    def __call__(self, images, subjects):
        scene_prompts = [p for ps in SCENES.values() for p in ps]
        groups = [g for g, ps in SCENES.items() for _ in ps]
        subj_prompts = [f'a photo of a {s}' for s in subjects]
        out = []
        for i in range(0, len(images), 16):
            batch = images[i:i + 16]
            sp = self._clip_probs(batch, scene_prompts)
            pp = self._clip_probs(batch, subj_prompts + EMPTY_PROMPTS)
            inp = self.owl_proc(text=[[f'a photo of a {s}' for s in subjects]] * len(batch), images=batch,
                                return_tensors='pt')
            det = self.owl(**inp)
            sizes = self.torch.tensor([[im.height, im.width] for im in batch])
            boxes = self.owl_proc.post_process_object_detection(det, threshold=BOX_MIN_SCORE, target_sizes=sizes)
            for j, im in enumerate(batch):
                scene = {g: 0.0 for g in SCENES}
                for g, p in zip(groups, sp[j].tolist()):
                    scene[g] = max(scene[g], p)   # max per group (calibrated)
                presence = pp[j].tolist()
                per_subject = dict(zip(subjects, presence[:len(subjects)]))
                best_area, best_label = 0.0, ''
                b = boxes[j]
                for score, label, box in zip(b['scores'].tolist(), b['labels'].tolist(), b['boxes'].tolist()):
                    x0, y0, x1, y1 = box
                    area = max(0.0, x1 - x0) * max(0.0, y1 - y0) / (im.width * im.height)
                    if area > best_area:
                        best_area, best_label = area, subjects[label]
                out.append({'scene': scene, 'subjects': per_subject,
                            'subject_p': sum(presence[:len(subjects)]), 'box_area': round(best_area, 4),
                            'box_label': best_label})
        return out


@dataclass
class FrameResult:
    t: float
    scene: str
    underwater_p: float
    subject_p: float
    present: bool
    distance: str
    subjects: dict = field(default_factory=dict)
    box_label: str = ''


def classify(raw: dict, t: float) -> FrameResult:
    scene = max(raw['scene'], key=raw['scene'].get)
    present = raw['subject_p'] >= 0.5 or raw['box_area'] >= MEDIUM_AREA
    return FrameResult(t=t, scene=scene, underwater_p=round(raw['scene'].get('underwater', 0.0), 3),
                       subject_p=round(raw['subject_p'], 3), present=present,
                       distance=closeness(raw['box_area'], present) if scene != 'card' else 'none',
                       subjects={k: round(v, 3) for k, v in raw['subjects'].items()}, box_label=raw['box_label'])


def sample_frames(video: Path, out_dir: Path, every_s: float = 1.0, until_s: float | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob('f_*.jpg'):
        old.unlink()
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(video)]
    if until_s:
        cmd += ['-t', f'{until_s:.2f}']
    # sample in the middle of each interval (avoids cross-dissolve frames at exact cut points)
    cmd += ['-vf', f'fps=1/{every_s}:start_time={every_s / 2},scale=640:-2', '-q:v', '3', str(out_dir / 'f_%05d.jpg')]
    subprocess.run(cmd, check=True)
    return sorted(out_dir.glob('f_*.jpg'))


def _entropy(counts: dict) -> float:
    n = sum(counts.values())
    return -sum(c / n * math.log2(c / n) for c in counts.values() if c) if n else 0.0


def evaluate(frames: list[FrameResult], shots: list[dict], targets: dict | None = None,
             footage_end_s: float | None = None) -> dict:
    """Aggregate frame results with the shot list (render report 'shots', each with 'seconds')."""
    tg = {**VISUAL_STANDARD, **(targets or {})}
    end = footage_end_s if footage_end_s is not None else sum(s['seconds'] for s in shots)
    fr = [f for f in frames if f.t < end]
    n = max(1, len(fr))
    share = lambda pred: round(sum(1 for f in fr if pred(f)) / n, 3)
    metrics = {
        'frames': len(fr),
        'subject_visible': share(lambda f: f.present),
        'close': share(lambda f: f.distance == 'close'),
        'close_or_medium': share(lambda f: f.distance in ('close', 'medium')),
        'underwater': share(lambda f: f.scene == 'underwater'),
        'empty': share(lambda f: not f.present),
        'scenes': {s: share(lambda f, s=s: f.scene == s) for s in SCENES},
    }
    # per-shot view
    t, shot_rows = 0.0, []
    for s in shots:
        a, b = t, t + s['seconds']
        t = b
        inside = [f for f in fr if a <= f.t < b] or [min(fr, key=lambda f: abs(f.t - (a + b) / 2))] if fr else []
        if not inside:
            continue
        vis = sum(1 for f in inside if f.present) / len(inside)
        scene = max(SCENES, key=lambda g: sum(1 for f in inside if f.scene == g))
        dist_rank = {'close': 3, 'medium': 2, 'far': 1, 'none': 0}
        dist = sorted((f.distance for f in inside), key=dist_rank.get)[len(inside) // 2]
        expect = s.get('expect') or ''
        match = None
        if expect:
            hits = [f for f in inside if f.subjects.get(expect, 0) >= 0.35 or (f.box_label == expect and f.present)]
            match = len(hits) / len(inside) >= 0.5
        shot_rows.append({'index': s.get('index'), 'clip': s.get('clip'), 'start_s': round(a, 2),
                          'seconds': round(s['seconds'], 2), 'type': f'{scene}/{dist}', 'subject_visible': round(vis, 2),
                          'expect': expect, 'expect_visible': match, 'note': s.get('note', '')})
    types: dict[str, int] = {}
    run, worst_run, prev = 0, 0, None
    for r in shot_rows:
        types[r['type']] = types.get(r['type'], 0) + 1
        run = run + 1 if r['type'] == prev else 1
        worst_run, prev = max(worst_run, run), r['type']
    lens = [r['seconds'] for r in shot_rows] or [0]
    checked = [r for r in shot_rows if r['expect_visible'] is not None]
    hook = [f for f in fr if f.t < 5.0]
    metrics.update({
        'shots': len(shot_rows), 'distinct_clips': len({r['clip'] for r in shot_rows}),
        'mean_shot_s': round(sum(lens) / len(lens), 2), 'max_shot_s': round(max(lens), 2),
        'shot_types': len(types), 'shot_type_counts': types, 'shot_type_entropy': round(_entropy(types), 2),
        'same_type_run_max': worst_run,
        'narration_match': round(sum(1 for r in checked if r['expect_visible']) / len(checked), 3) if checked else None,
        'hook_subject': round(sum(1 for f in hook if f.present) / len(hook), 2) if hook else 0.0,
        'hook_close_or_underwater': any(f.present and (f.distance in ('close', 'medium') or f.scene == 'underwater')
                                        for f in hook),
    })
    checks = {
        'subject_visible': metrics['subject_visible'] >= tg['subject_visible_min'],
        'close_or_medium': metrics['close_or_medium'] >= tg['close_or_medium_min'],
        'underwater': metrics['underwater'] >= tg['underwater_min'],
        'empty': metrics['empty'] <= tg['empty_max'],
        'max_shot': metrics['max_shot_s'] <= tg['max_shot_s'],
        'mean_shot': metrics['mean_shot_s'] <= tg['mean_shot_s_max'],
        'variety': metrics['shot_types'] >= tg['shot_types_min'] and worst_run <= tg['same_type_run_max'],
        'narration_match': metrics['narration_match'] is None or metrics['narration_match'] >= tg['narration_match_min'],
        'hook': metrics['hook_subject'] >= tg['hook_subject_min']
                and (metrics['hook_close_or_underwater'] or not tg['hook_close_or_underwater']),
    }
    return {'standard': tg, 'metrics': metrics, 'checks': checks, 'passed': all(checks.values()),
            'failed': [k for k, ok in checks.items() if not ok], 'shots': shot_rows}


def annotated_sheet(frames: list[Path], results: list[FrameResult], out: Path, cols: int = 8) -> None:
    """Grid of the sampled frames with what the models decided (for a human check)."""
    from PIL import Image, ImageDraw, ImageFont
    if not frames:
        return
    thumbs = []
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
    except OSError:
        font = ImageFont.load_default()
    for p, r in zip(frames, results):
        im = Image.open(p).convert('RGB')
        im.thumbnail((240, 135))
        d = ImageDraw.Draw(im)
        colour = {'close': (40, 200, 90), 'medium': (230, 190, 40), 'far': (240, 120, 40), 'none': (220, 50, 50)}[r.distance]
        d.rectangle([0, 0, im.width - 1, im.height - 1], outline=colour, width=4)
        d.rectangle([0, 0, im.width, 17], fill=(0, 0, 0))
        d.text((4, 2), f'{int(r.t // 60)}:{int(r.t % 60):02d} {r.scene[:5]} {r.distance}', fill=colour, font=font)
        thumbs.append(im)
    w, h = 240, 135
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new('RGB', (cols * w, rows * h), (10, 10, 10))
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(out, quality=82)


def analyze_video(video: Path, shots: list[dict], subjects: list[str], out_dir: Path, *,
                  footage_end_s: float | None = None, targets: dict | None = None,
                  scorer: Callable | None = None, every_s: float = 1.0) -> dict:
    from PIL import Image
    out_dir = Path(out_dir)
    paths = sample_frames(video, out_dir / 'frames', every_s, footage_end_s)
    scorer = scorer or ModelScorer()
    images = [Image.open(p).convert('RGB') for p in paths]
    raw = scorer(images, subjects)
    results = [classify(r, every_s / 2 + i * every_s) for i, r in enumerate(raw)]
    report = evaluate(results, shots, targets, footage_end_s)
    report['subjects'] = subjects
    report['models'] = getattr(scorer, 'models', None)
    report['frames_detail'] = [f.__dict__ for f in results]
    for i in range(0, len(paths), 120):   # one sheet per 2 minutes
        annotated_sheet(paths[i:i + 120], results[i:i + 120], out_dir / f'visual_sheet_{i // 120}.jpg')
    (out_dir / 'visual_qa.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    for p in paths:
        p.unlink()
    return report


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description='Visual QA of a rendered documentary (render_report.json + MP4)')
    ap.add_argument('--video', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True, help='render_report.json')
    ap.add_argument('--plan', type=Path, help='plan JSON (subjects, expect, visual_targets)')
    ap.add_argument('--subjects', default='', help='";"-separated subjects (overrides the plan)')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    rep = json.loads(args.report.read_text(encoding='utf-8'))
    plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else {}
    subjects = [s.strip() for s in args.subjects.split(';') if s.strip()] or plan.get('subjects') or ['whale', 'sea turtle']
    shots = rep['shots']
    if plan:   # shot 'expect' comes from the plan (same order as the render report)
        flat = [s for b in plan['beats'] for s in b['shots']]
        for s, p in zip(shots, flat):
            s.setdefault('expect', p.get('expect', ''))
    footage_end = sum(s['seconds'] for s in shots)
    result = analyze_video(args.video, shots, subjects, args.out, footage_end_s=footage_end,
                           targets=plan.get('visual_targets'))
    print(json.dumps({'passed': result['passed'], 'failed': result['failed'],
                      **{k: v for k, v in result['metrics'].items() if k != 'shot_type_counts'}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
