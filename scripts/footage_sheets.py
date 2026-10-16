"""Download exact Commons clips (by title) and make timestamped contact sheets for review.

Re-checks every clip's licence at download time; writes clips.json with full
description, author, licence, licence URL, file page and whether the clip has
an audio track. No AI footage is created.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import httpx
from channel.commons import API, USER_AGENT, _clean, license_allowed
from channel.footage import _best_derivative, download_clip


def clip_info(client: httpx.Client, title: str) -> dict:
    r = client.get(API, params={'action': 'query', 'format': 'json', 'formatversion': '2', 'titles': title,
                                'prop': 'videoinfo', 'viprop': 'url|size|mime|extmetadata|derivatives'},
                   headers={'User-Agent': USER_AGENT}, timeout=30)
    r.raise_for_status()
    page = r.json()['query']['pages'][0]
    if page.get('missing'):
        raise ValueError('missing file: ' + title)
    info = (page.get('videoinfo') or [{}])[0]
    meta = info.get('extmetadata') or {}
    lic = _clean((meta.get('LicenseShortName') or {}).get('value'))
    if not license_allowed(lic) or _clean((meta.get('Restrictions') or {}).get('value')):
        raise ValueError(f'licence not allowed for {title}: {lic}')
    deriv = _best_derivative(info)
    if deriv is None:
        raise ValueError('no downloadable version for ' + title)
    desc = ' '.join(_clean((meta.get('ImageDescription') or {}).get('value')).split())
    return {'title': page['title'], 'license': lic, 'license_url': _clean((meta.get('LicenseUrl') or {}).get('value')),
            'author': _clean((meta.get('Artist') or {}).get('value')) or 'Unknown author',
            'credit': _clean((meta.get('Credit') or {}).get('value')),
            'description': desc[:600], 'page': info.get('descriptionurl') or '',
            'duration_s': float(info.get('duration') or 0), 'download': deriv['src'],
            'download_height': deriv.get('height')}


def resolve_title(client: httpx.Client, terms: str, prefix: str) -> str:
    """Full File: title of the search result whose title starts with ``prefix``."""
    r = client.get(API, params={'action': 'query', 'format': 'json', 'formatversion': '2', 'list': 'search',
                                'srsearch': f'filetype:video {terms}', 'srnamespace': '6', 'srlimit': '50'},
                   headers={'User-Agent': USER_AGENT}, timeout=30)
    r.raise_for_status()
    want = prefix if prefix.startswith('File:') else 'File:' + prefix
    for hit in r.json().get('query', {}).get('search', []):
        if hit['title'].startswith(want):
            return hit['title']
    raise ValueError('no title starting with ' + want)


def has_audio(path: Path) -> bool:
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                        '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return bool(p.stdout.strip())


def sheet(path: Path, out: Path, every: float) -> None:
    vf = (f"fps=1/{every},scale=320:-2,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
          f"text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,tile=6x6:padding=3:margin=3")
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-vf', vf,
                    '-frames:v', '1', '-q:v', '4', str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--titles', required=True, help='"|"-separated exact File: titles')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    clips = []
    with httpx.Client(trust_env=True) as client:
        for i, item in enumerate(t.strip() for t in args.titles.split('|') if t.strip()):
            # "search terms::title prefix" or an exact title
            title = resolve_title(client, *item.split('::', 1)) if '::' in item else item
            info = clip_info(client, title)
            ext = '.webm' if info['download'].endswith('.webm') else '.mp4'
            path = download_clip(client, info['download'], args.out / f'clip_{i}{ext}')
            info.update(file=path.name, has_audio=has_audio(path))
            every = max(2.0, round(info['duration_s'] / 36, 1))
            sheet(path, args.out / f'clip_{i}_sheet.jpg', every)
            info['sheet_every_s'] = every
            clips.append(info)
    (args.out / 'clips.json').write_text(json.dumps(clips, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps([{k: c[k] for k in ('title', 'license', 'author', 'duration_s', 'has_audio', 'sheet_every_s')} for c in clips], ensure_ascii=False))


if __name__ == '__main__':
    main()
