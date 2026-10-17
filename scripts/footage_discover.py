"""Find and rank real wildlife clips for a documentary, by what is actually on screen.

1. Collect candidates: Wikimedia Commons (categories walked recursively + text
   search) and Pixabay (API search). Licence filter as in footage mode; Commons
   clips flagged "License review needed" are kept but marked, never auto-approved.
2. Download a small review copy (<= 480p), sample one frame per second and score
   every second with the visual QA models (subject in frame, distance, under water).
3. Rank clips and propose the best windows (default 5 s) — close shots and
   underwater shots of the subject first, empty sea and landscapes last.

Output: discover.json (+ an annotated frame sheet per clip). Nothing is published;
the workflow ships the pack encrypted. Clip choice stays a human decision: the
models only sort the pile.
"""
from __future__ import annotations
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import httpx
from channel.commons import API, USER_AGENT, _clean, license_allowed
from channel.footage import ALLOWED_HOSTS, _AI_HINT, download_clip

VIDEO_EXT = re.compile(r'\.(webm|ogv|ogg|mpg|mpeg|mp4|mov)$', re.I)


def _api(client: httpx.Client, **params) -> dict:
    params = {'action': 'query', 'format': 'json', 'formatversion': '2', **params}
    for attempt in range(4):
        r = client.get(API, params=params, headers={'User-Agent': USER_AGENT}, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


def walk_category(client: httpx.Client, root: str, *, depth: int = 2, max_cats: int = 120) -> set[str]:
    """Video file titles under ``root`` (subcategories down to ``depth``)."""
    seen_cats, files, queue = set(), set(), [(root if root.startswith('Category:') else 'Category:' + root, 0)]
    while queue and len(seen_cats) < max_cats:
        cat, d = queue.pop(0)
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        cont = {}
        while True:
            data = _api(client, list='categorymembers', cmtitle=cat, cmtype='file|subcat', cmlimit='500', **cont)
            for m in data.get('query', {}).get('categorymembers', []):
                t = m['title']
                if t.startswith('Category:') and d < depth:
                    queue.append((t, d + 1))
                elif t.startswith('File:') and VIDEO_EXT.search(t):
                    files.add(t)
            if 'continue' not in data:
                break
            cont = {'cmcontinue': data['continue']['cmcontinue']}
    return files


def search_titles(client: httpx.Client, terms: str, limit: int = 50) -> set[str]:
    data = _api(client, list='search', srsearch=f'filetype:video {terms}', srnamespace='6', srlimit=str(limit))
    return {h['title'] for h in data.get('query', {}).get('search', [])}


def _review_derivative(info: dict, max_h: int = 480) -> dict | None:
    best = None
    for d in info.get('derivatives') or []:
        src, h = d.get('src') or '', int(d.get('height') or 0)
        if urlparse(src).hostname not in ALLOWED_HOSTS or not (d.get('type') or '').startswith('video/'):
            continue
        if 240 <= h <= max_h and (best is None or h > int(best['height'] or 0)):
            best = d
    return best


def commons_candidates(client: httpx.Client, titles: set[str], min_height: int = 720) -> tuple[list[dict], dict]:
    out, rejects = [], {}
    titles = sorted(titles)
    for i in range(0, len(titles), 40):
        data = _api(client, titles='|'.join(titles[i:i + 40]), prop='videoinfo|categories', cllimit='max',
                    viprop='url|size|mime|extmetadata|derivatives|mediatype')
        for page in data.get('query', {}).get('pages', []):
            info = (page.get('videoinfo') or [{}])[0]
            meta = info.get('extmetadata') or {}
            lic = _clean((meta.get('LicenseShortName') or {}).get('value'))
            desc = _clean((meta.get('ImageDescription') or {}).get('value'))
            cats = [c['title'].removeprefix('Category:') for c in page.get('categories', [])]
            h, dur = int(info.get('height') or 0), float(info.get('duration') or 0)
            why = ('license' if not license_allowed(lic) or str((meta.get('NonFree') or {}).get('value') or '').lower() == 'true' else
                   'restricted' if _clean((meta.get('Restrictions') or {}).get('value')) else
                   'ai_or_cgi' if _AI_HINT.search(page['title'] + ' ' + desc) else
                   'low_res' if h < min_height else 'too_short' if dur < 4 else '')
            review = None if why else _review_derivative(info)
            if not why and review is None:
                why = 'no_review_copy'
            if why:
                rejects[why] = rejects.get(why, 0) + 1
                continue
            out.append({'source': 'commons', 'id': page['title'], 'title': page['title'], 'license': lic,
                        'author': _clean((meta.get('Artist') or {}).get('value')) or 'Unknown author',
                        'description': desc[:400], 'page': info.get('descriptionurl') or '', 'height': h,
                        'duration_s': round(dur, 1), 'review_url': review['src'],
                        'license_review_pending': any('License review needed' in c for c in cats)})
    return out, rejects


def pixabay_candidates(client: httpx.Client, queries: list[str], tag_filter: str, min_width: int = 1280) -> tuple[list[dict], dict]:
    from channel import pixabay
    seen, info = {}, {}
    pat = re.compile(tag_filter, re.I) if tag_filter else None
    for q in queries:
        clips, meta = pixabay.search(client, q, min_width=min_width)
        info[q] = meta
        for c in clips:
            if c['id'] in seen or not c['review'] or (pat and not pat.search(c['tags'])):
                continue
            seen[c['id']] = {'source': 'pixabay', 'id': c['id'], 'title': f"Pixabay #{c['id']}", 'license': c['license'],
                             'author': c['author'], 'description': c['tags'], 'page': c['page'],
                             'height': c['best']['height'], 'duration_s': c['duration_s'],
                             'review_url': c['review']['url'], 'license_review_pending': False,
                             'species_verified': False, 'ai_checked_on_page': False}
    return list(seen.values()), info


def best_windows(per_second: list[dict], window: int = 5, top: int = 3) -> list[dict]:
    """Non-overlapping windows with the highest 'value' (subject present, close, under water)."""
    def value(f):
        if not f['present']:
            return 0.0
        return 1.0 + {'close': 1.2, 'medium': 0.6, 'far': 0.0, 'none': 0.0}[f['distance']] + (0.8 if f['scene'] == 'underwater' else 0.0)
    vals = [value(f) for f in per_second]
    cands = []
    for s in range(0, max(1, len(vals) - window + 1)):
        seg = vals[s:s + window]
        if len(seg) < min(window, len(vals)):
            continue
        cands.append((sum(seg) / len(seg), s))
    picked = []
    for score, s in sorted(cands, reverse=True):
        if score <= 1.0 or len(picked) >= top:
            break
        if all(abs(s - p['start_s']) >= window for p in picked):
            fr = per_second[s:s + window]
            picked.append({'start_s': s, 'end_s': s + len(fr), 'value': round(score, 2),
                           'types': sorted({f"{f['scene']}/{f['distance']}" for f in fr})})
    return picked


def score_clip(path: Path, scorer, subjects: list[str], out_dir: Path, tag: str, max_s: float = 300) -> dict:
    from PIL import Image
    from channel.visual_qa import annotated_sheet, classify, sample_frames
    frames = sample_frames(path, out_dir / 'frames', 1.0, max_s)
    images = [Image.open(p).convert('RGB') for p in frames]
    res = [classify(r, 0.5 + i) for i, r in enumerate(scorer(images, subjects))] if images else []
    annotated_sheet(frames, res, out_dir / f'sheet_{tag}.jpg', cols=10)
    for p in frames:
        p.unlink()
    per = [{'t': f.t, 'scene': f.scene, 'present': f.present, 'distance': f.distance,
            'subjects': f.subjects} for f in res]
    n = max(1, len(per))
    return {'seconds_scored': len(per),
            'subject_s': sum(1 for f in per if f['present']),
            'close_s': sum(1 for f in per if f['present'] and f['distance'] == 'close'),
            'medium_s': sum(1 for f in per if f['present'] and f['distance'] == 'medium'),
            'underwater_s': sum(1 for f in per if f['scene'] == 'underwater'),
            'underwater_subject_s': sum(1 for f in per if f['present'] and f['scene'] == 'underwater'),
            'subject_share': round(sum(1 for f in per if f['present']) / n, 2),
            'windows': best_windows(per), 'per_second': per, 'sheet': f'sheet_{tag}.jpg'}


def slate(path: Path, out: Path, tag: str) -> None:
    """Readable frames of the opening slate (credits, permit numbers) — first 12 s."""
    import subprocess
    vf = ("fps=1/1.5,scale=640:-2,tile=4x2:padding=4:margin=4")
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-t', '12', '-i', str(path), '-vf', vf,
                    '-frames:v', '1', '-q:v', '3', str(out / f'slate_{tag}.jpg')], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--categories', default='', help='";"-separated Commons categories')
    ap.add_argument('--searches', default='', help='";"-separated Commons searches')
    ap.add_argument('--titles', default='', help='"|"-separated exact Commons titles to include')
    ap.add_argument('--pixabay', default='', help='";"-separated Pixabay searches (needs PIXABAY_API_KEY)')
    ap.add_argument('--noaa', default='', help='";"-separated NOAA Fisheries B-roll video ids')
    ap.add_argument('--pixabay-tags', default='', help='regex the Pixabay tags must match')
    ap.add_argument('--subjects', required=True, help='";"-separated subjects for the models')
    ap.add_argument('--exclude', default='', help='regex on title/description to drop (e.g. aquarium|captive)')
    ap.add_argument('--max-clips', type=int, default=60)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    subjects = [s.strip() for s in a.subjects.split(';') if s.strip()]
    report = {'subjects': subjects, 'rejects': {}, 'clips': []}
    with httpx.Client(trust_env=True) as client:
        titles = {t.strip() for t in a.titles.split('|') if t.strip()}
        for c in filter(None, (x.strip() for x in a.categories.split(';'))):
            try:
                found = walk_category(client, c)
            except httpx.HTTPError as exc:
                report['rejects'][f'category {c}'] = type(exc).__name__; continue
            report.setdefault('categories', {})[c] = len(found)
            titles |= found
        for s in filter(None, (x.strip() for x in a.searches.split(';'))):
            titles |= search_titles(client, s)
        cands, rej = commons_candidates(client, titles) if titles else ([], {})
        report['rejects'].update(rej)
        if a.pixabay.strip():
            px, meta = pixabay_candidates(client, [q.strip() for q in a.pixabay.split(';') if q.strip()], a.pixabay_tags)
            report['pixabay_queries'] = meta
            cands += px
        if a.noaa.strip():
            from channel import noaa
            cands = [{**noaa.info(int(v)), 'review_url': ''} for v in a.noaa.split(';') if v.strip()] + cands
        if a.exclude:
            ex = re.compile(a.exclude, re.I)
            dropped = [c for c in cands if c['source'] != 'noaa' and ex.search(c['title'] + ' ' + c['description'])]
            report['rejects']['excluded'] = len(dropped)
            cands = [c for c in cands if c not in dropped]
        report['candidates'] = len(cands)
        cands = cands[:a.max_clips]
        from channel.visual_qa import ModelScorer
        scorer = ModelScorer()
        report['models'] = scorer.models
        for i, c in enumerate(cands):
            tag = f'{i:02d}'
            try:
                if c['source'] == 'noaa':
                    from channel import noaa
                    path = noaa.download(client, c['id'], a.out / 'review' / f'{tag}.mp4')
                    slate(path, a.out, tag)
                elif c['source'] == 'pixabay':
                    from channel import pixabay
                    path = pixabay.download(client, c['review_url'], a.out / 'review' / f'{tag}.mp4')
                else:
                    path = download_clip(client, c['review_url'], a.out / 'review' / f'{tag}.webm')
                c.update(score_clip(path, scorer, subjects, a.out, tag))
                path.unlink()
            except Exception as exc:   # one bad clip must not stop the search
                c['error'] = f'{type(exc).__name__}: {str(exc)[:160]}'
            c['tag'] = tag
            report['clips'].append(c)
    rank = lambda c: (c.get('underwater_subject_s', 0) * 2 + c.get('close_s', 0) * 2 + c.get('medium_s', 0)
                      + c.get('subject_s', 0) * 0.3)
    report['clips'].sort(key=rank, reverse=True)
    (a.out / 'discover.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    for c in report['clips']:
        print(json.dumps({k: c.get(k) for k in ('tag', 'title', 'duration_s', 'license', 'license_review_pending', 'subject_s',
                                                 'close_s', 'medium_s', 'underwater_subject_s', 'windows', 'error')},
                         ensure_ascii=False))


if __name__ == '__main__':
    main()
