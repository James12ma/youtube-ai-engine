"""Pixabay video search for footage mode (free API, key from the PIXABAY_API_KEY secret).

Safety rules
- The key is read from the environment only and is never printed, logged,
  written to a report or included in an exception message.
- Only real filmed clips are considered (video_type=film); clips whose tags
  hint at AI/CGI/animation are rejected. The API has NO AI-generated flag, so
  every clip still needs a human/visual check and a page check before use.
- Tags are user-written: a tag such as "humpback" is NOT proof of species.
  Results stay "species_unverified" until someone confirms them visually.
- Licence: Pixabay Content License (commercial use allowed, attribution
  optional, no standalone redistribution, no warranty about third-party
  rights). We still credit the author and Pixabay in every video.
- Results are cached for 24 h (API rule); downloads are limited to clips we
  actually review or use (no bulk downloading).
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import httpx

API = 'https://pixabay.com/api/videos/'
ALLOWED_HOSTS = {'cdn.pixabay.com'}
LICENSE = 'Pixabay Content License'
LICENSE_URL = 'https://pixabay.com/service/license-summary/'
MAX_BYTES = 400_000_000
_AI_TAG = re.compile(r'\b(ai|a\.i\.|ai[- ]generated|generated|generative|midjourney|sora|runway|cgi|3d|render(ed)?|'
                     r'animation|animated|cartoon|illustration|digital art|fantasy|virtual)\b', re.I)


class PixabayError(RuntimeError):
    pass


def api_key() -> str:
    key = os.environ.get('PIXABAY_API_KEY', '').strip()
    if not key:
        raise PixabayError('PIXABAY_API_KEY secret is not set')
    return key


def _get(client: httpx.Client, params: dict) -> dict:
    """GET the API; errors never include the request URL (it contains the key)."""
    for attempt in range(3):
        try:
            r = client.get(API, params={'key': api_key(), **params}, timeout=30)
        except httpx.HTTPError as exc:
            raise PixabayError('network error: ' + type(exc).__name__) from None
        if r.status_code == 429 and attempt < 2:
            time.sleep(30)
            continue
        if r.status_code != 200:
            raise PixabayError(f'HTTP {r.status_code}: {r.text[:120].replace(api_key(), "***")}')
        return r.json()
    raise PixabayError('rate limited')


def best_rendition(videos: dict, max_height: int = 2160) -> dict | None:
    best = None
    for name in ('large', 'medium', 'small', 'tiny'):
        v = videos.get(name) or {}
        url, h = v.get('url') or '', int(v.get('height') or 0)
        if not url or urlparse(url).hostname not in ALLOWED_HOSTS or h > max_height:
            continue
        if best is None or h > best['height']:
            best = {'name': name, 'url': url, 'width': int(v.get('width') or 0), 'height': h,
                    'size': int(v.get('size') or 0), 'thumbnail': v.get('thumbnail') or ''}
    return best


def review_rendition(videos: dict) -> dict | None:
    """Smallest rendition (for contact sheets) — saves bandwidth."""
    for name in ('tiny', 'small', 'medium'):
        v = videos.get(name) or {}
        if v.get('url') and urlparse(v['url']).hostname in ALLOWED_HOSTS:
            return {'name': name, 'url': v['url'], 'height': int(v.get('height') or 0)}
    return None


def normalize(hit: dict, query: str) -> tuple[dict | None, str]:
    tags = hit.get('tags') or ''
    if (hit.get('type') or 'film') != 'film':
        return None, 'not_film'
    if _AI_TAG.search(tags):
        return None, 'ai_or_cgi_tag'
    best = best_rendition(hit.get('videos') or {})
    if best is None:
        return None, 'no_download'
    return ({'id': int(hit['id']), 'page': hit.get('pageURL') or '', 'tags': tags, 'duration_s': hit.get('duration'),
             'author': hit.get('user') or 'Unknown', 'author_id': hit.get('user_id'),
             'best': best, 'review': review_rendition(hit.get('videos') or {}),
             'license': LICENSE, 'license_url': LICENSE_URL, 'query': query,
             'species_verified': False, 'ai_checked_on_page': False}, '')


def search(client: httpx.Client, query: str, *, min_width: int = 1920, per_page: int = 100) -> tuple[list[dict], dict]:
    data = _get(client, {'q': query[:100], 'video_type': 'film', 'min_width': str(min_width),
                         'per_page': str(per_page), 'safesearch': 'true'})
    clips, rejects = [], {}
    for hit in data.get('hits', []):
        clip, why = normalize(hit, query)
        if why:
            rejects[why] = rejects.get(why, 0) + 1
        else:
            clips.append(clip)
    return clips, {'total': data.get('totalHits'), 'rejected': rejects}


def get_video(client: httpx.Client, video_id: int) -> dict:
    data = _get(client, {'id': str(int(video_id))})
    hits = data.get('hits') or []
    if not hits:
        raise PixabayError(f'video {video_id} not found')
    clip, why = normalize(hits[0], f'id:{video_id}')
    if why:
        raise PixabayError(f'video {video_id} rejected: {why}')
    return clip


def download(client: httpx.Client, url: str, dest: Path) -> Path:
    if urlparse(url).hostname not in ALLOWED_HOSTS or urlparse(url).scheme != 'https':
        raise PixabayError('download host not allowed')
    with client.stream('GET', url, timeout=120, follow_redirects=False) as r:
        if r.status_code != 200:
            raise PixabayError(f'download HTTP {r.status_code}')
        dest.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with dest.open('wb') as fh:
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise PixabayError('clip too large')
                fh.write(chunk)
    return dest


def audit(queries: list[str], out: Path, *, review_limit: int = 40) -> dict:
    """Search, dedupe and download small review copies of the most promising clips."""
    import subprocess
    out.mkdir(parents=True, exist_ok=True)
    seen: dict[int, dict] = {}
    per_query = {}
    with httpx.Client(trust_env=True) as client:
        for q in queries:
            clips, meta = search(client, q)
            per_query[q] = {**meta, 'usable_1080p_plus': len(clips)}
            for c in clips:
                if c['id'] in seen:
                    seen[c['id']]['also_matched'] = seen[c['id']].get('also_matched', []) + [q]
                else:
                    seen[c['id']] = c
        ranked = list(seen.values())[:review_limit]
        for i, c in enumerate(ranked):
            if not c['review']:
                continue
            path = download(client, c['review']['url'], out / 'review' / f"px_{c['id']}.mp4")
            dur = float(c['duration_s'] or 10)
            sheet = out / f"sheet_{i:02d}_{c['id']}.jpg"
            every = max(1.0, round(dur / 12, 1))
            vf = (f"fps=1/{every},scale=320:-2,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                  f"text='{c['id']} %{{pts\\:hms}}':x=4:y=4:fontsize=14:fontcolor=white:box=1:boxcolor=black@0.6,"
                  "tile=4x3:padding=2:margin=2")
            subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-vf', vf,
                            '-frames:v', '1', '-q:v', '5', str(sheet)], check=True)
            c['sheet'] = sheet.name
            c['sheet_every_s'] = every
            path.unlink()
    report = {'queries': per_query, 'unique_clips': len(seen), 'reviewed': min(len(seen), review_limit),
              'clips': list(seen.values()), 'cached_at': int(time.time())}
    (out / 'pixabay_audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Pixabay footage audit (needs PIXABAY_API_KEY)')
    ap.add_argument('--queries', required=True, help='semicolon-separated')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--review-limit', type=int, default=40)
    args = ap.parse_args()
    try:
        rep = audit([q.strip() for q in args.queries.split(';') if q.strip()], args.out, review_limit=args.review_limit)
    except PixabayError as exc:
        print(json.dumps({'error': str(exc)}))
        raise SystemExit(2)
    print(json.dumps({'queries': rep['queries'], 'unique_clips': rep['unique_clips']}, ensure_ascii=False))
