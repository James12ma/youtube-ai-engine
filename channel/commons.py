"""Free-licensed photos from Wikimedia Commons for storyboard 'broll' scenes.

Only files whose licence is public domain, CC0, CC BY or CC BY-SA are used,
and every photo used gets a credit line (author, licence, file page) for the
video description. Nothing is uploaded or published here.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
import httpx

API = 'https://commons.wikimedia.org/w/api.php'
USER_AGENT = 'Alan7VideoEngine/1.0 (https://github.com/James12ma/youtube-ai-engine; owner-reviewed educational videos)'
ALLOWED_DOWNLOAD_HOSTS = {'upload.wikimedia.org'}
MAX_IMAGE_BYTES = 12_000_000
MIN_WIDTH = 1200
_ALLOWED_LICENSE = re.compile(r'^(public domain|pd\b.*|cc0.*|cc[ -]by(-sa)?[ -]\d(\.\d)?.*|cc[ -]by(-sa)?)$', re.I)
_BLOCKED_TERMS = re.compile(r'\b(logo|brand|trademark|person|people|man|woman|child|face|portrait)\b', re.I)


LAST_SEARCH: dict = {}


class CommonsError(RuntimeError):
    pass


def _clean(text: str | None) -> str:
    text = re.sub(r'<[^>]+>', '', text or '')
    return ' '.join(html.unescape(text).split())[:200]


def license_allowed(short_name: str) -> bool:
    return bool(_ALLOWED_LICENSE.match((short_name or '').strip()))


def search_photo(client: httpx.Client, terms: str, exclude: set[str], *, allow_portrait: bool = False) -> dict | None:
    """Best free-licensed, landscape-ish, large bitmap for ``terms``; None if nothing qualifies."""
    LAST_SEARCH.clear()
    terms = ' '.join(terms.split())[:60]
    if not terms or _BLOCKED_TERMS.search(terms):
        return None
    params = {'action': 'query', 'format': 'json', 'formatversion': '2', 'generator': 'search',
              'gsrsearch': f'filetype:bitmap {terms}', 'gsrnamespace': '6', 'gsrlimit': '20',
              'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': '1920'}
    response = client.get(API, params=params, headers={'User-Agent': USER_AGENT}, timeout=20)
    response.raise_for_status()
    body = response.json()
    pages = sorted(body.get('query', {}).get('pages', []), key=lambda p: p.get('index', 999))
    LAST_SEARCH.update({'pages': len(pages), 'error': (body.get('error') or {}).get('code'),
                        'with_imageinfo': sum(1 for p in pages if p.get('imageinfo'))})
    rejects: dict[str, int] = {}
    for page in pages:
        info = (page.get('imageinfo') or [{}])[0]
        meta = info.get('extmetadata') or {}
        lic = _clean((meta.get('LicenseShortName') or {}).get('value'))
        url = info.get('thumburl') or info.get('url') or ''
        width, height = int(info.get('width') or 0), int(info.get('height') or 1)
        why = ('reused' if page.get('title') in exclude else
               'mime' if info.get('mime') not in ('image/jpeg', 'image/png') else
               'license' if not license_allowed(lic) else
               'small' if width < MIN_WIDTH else
               'portrait' if (not allow_portrait and width < height) else
               'host' if (urlparse(url).hostname not in ALLOWED_DOWNLOAD_HOSTS or urlparse(url).scheme != 'https') else '')
        if why:
            rejects[why] = rejects.get(why, 0) + 1
            LAST_SEARCH['rejects'] = rejects
            continue
        return {'title': page['title'], 'url': url, 'license': lic,
                'author': _clean((meta.get('Artist') or {}).get('value')) or 'Unknown author',
                'page': info.get('descriptionurl') or '', 'search_terms': terms}
    return None


def download(client: httpx.Client, url: str, dest: Path) -> Path:
    if urlparse(url).hostname not in ALLOWED_DOWNLOAD_HOSTS or urlparse(url).scheme != 'https':
        raise CommonsError('download host not allowed')
    with client.stream('GET', url, headers={'User-Agent': USER_AGENT}, timeout=30, follow_redirects=False) as r:
        r.raise_for_status()
        data = bytearray()
        for chunk in r.iter_bytes():
            data += chunk
            if len(data) > MAX_IMAGE_BYTES:
                raise CommonsError('image too large')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(data))
    return dest


def fetch_for_storyboard(storyboard_path: Path, out_dir: Path, *,
                         client_factory: Callable[[], httpx.Client] = lambda: httpx.Client(trust_env=True)) -> dict:
    """Write photos, asset_map.json ({scene index: path}) and credits.json; returns a summary."""
    scenes = json.loads(Path(storyboard_path).read_text(encoding='utf-8'))['scenes']
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_map, credits, missing, used = {}, [], [], set()
    reasons: dict[str, str] = {}
    with client_factory() as client:
        for scene in scenes:
            if scene.get('visual_type') != 'broll':
                continue
            terms = scene.get('search_terms') or ''
            try:
                # Prefer landscape; a portrait photo is cropped to fill the frame.
                found = search_photo(client, terms, used) or search_photo(client, terms, used, allow_portrait=True)
            except httpx.HTTPStatusError as exc:
                found = None; reasons[str(scene['index'])] = f'search_http_{exc.response.status_code}'
            except (httpx.HTTPError, ValueError) as exc:
                found = None; reasons[str(scene['index'])] = 'search_' + type(exc).__name__
            if not found:
                diag = LAST_SEARCH
                reasons.setdefault(str(scene['index']), 'no_qualifying_photo'
                                   + (f" (pages={diag.get('pages')}, imageinfo={diag.get('with_imageinfo')}, error={diag.get('error')}, rejects={diag.get('rejects')})" if diag else ''))
                missing.append(scene['index'])
                continue
            suffix = '.png' if found['url'].lower().endswith('.png') else '.jpg'
            try:
                path = download(client, found['url'], out_dir / f"scene_{scene['index']}{suffix}")
            except httpx.HTTPStatusError as exc:
                reasons[str(scene['index'])] = f'download_http_{exc.response.status_code}'
                missing.append(scene['index'])
                continue
            except (httpx.HTTPError, CommonsError) as exc:
                reasons[str(scene['index'])] = 'download_' + type(exc).__name__
                missing.append(scene['index'])
                continue
            used.add(found['title'])
            asset_map[str(scene['index'])] = str(path)
            credits.append({**found, 'scene_index': scene['index']})
    (out_dir / 'asset_map.json').write_text(json.dumps(asset_map, indent=2), encoding='utf-8')
    (out_dir / 'credits.json').write_text(json.dumps(credits, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = ['Fotos (Wikimedia Commons):'] + [f"- {c['title'].removeprefix('File:')} — {c['author']}, {c['license']}, {c['page']}"
                                              for c in credits]
    (out_dir / 'credits.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    summary = {'photos': len(asset_map), 'missing_scenes': missing}
    if reasons:
        summary['missing_reasons'] = reasons
    return summary


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Fetch free-licensed Commons photos for broll scenes (no upload)')
    ap.add_argument('--storyboard', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(fetch_for_storyboard(args.storyboard, args.out)))
