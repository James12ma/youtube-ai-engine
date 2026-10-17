"""NOAA Fisheries video gallery B-roll (public domain, credit "NOAA Fisheries").

Terms on every B-roll page (videos.fisheries.noaa.gov, checked Oct 2026):
"B-roll packages are in the public domain and you can download them for use as
long as you credit NOAA Fisheries." Each package opens with a slate that lists
any other organisations' clips and permit numbers; those credits are copied by
hand into the plan (ClipSource.credit) after reading the slate.

Only B-roll packages are allowed here: NOAA's narrative videos may contain
licensed third-party clips that must not be extracted.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
import httpx

ACCOUNT, SITE = '659677166001', 'site-600408'
DOWNLOAD = 'https://download.gallery.brightcove.com/api/gallery/account/{a}/site/{s}/video/{v}/download'
PAGE = 'https://videos.fisheries.noaa.gov/detail/video/{v}'
LICENSE = 'Public domain (NOAA Fisheries B-roll)'
LICENSE_URL = 'https://videos.fisheries.noaa.gov/'
ALLOWED_SUFFIXES = ('.brightcove.com', '.brightcovecdn.com', '.akamaihd.net', '.cloudfront.net')
MAX_BYTES = 1_500_000_000

# B-roll packages reviewed by hand (title and description from the gallery page).
KNOWN = {
    3911325489001: {'title': 'B-Roll: Humpback Whales and Behavior',
                    'description': 'Underwater and topside footage of humpback whales near the surface. Filmed in Silver Bank, '
                                   'Dominican Republic, offshore of New England, and in Hawaii.',
                    # title cards (read 2026-10-17); 240.x still shows the card fading out
                    'slates': [(0, 9.0), (140.0, 143.0), (222.0, 225.2), (237.0, 240.9)]},
    2221891724001: {'title': 'B-Roll: Humpback Whale Research in the North Pacific', 'description': ''},
    4084488077001: {'title': 'B-Roll: Green Sea Turtle',
                    'description': 'Northwestern Hawaiian Islands, Papahānaumokuākea Marine National Monument. Underwater '
                                   'and topside beach footage of the endangered green sea turtle.',
                    'slates': [(0, 10.0), (103.0, 107.0), (164.0, 999.0)]},
}


class NoaaError(RuntimeError):
    pass


def _host_ok(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == 'https' and any((u.hostname or '').endswith(s) for s in ALLOWED_SUFFIXES)


def slate_conflicts(video_id: int, windows: list[tuple[float, float]], borrow: float = 0.6) -> list[str]:
    """Shot windows that would show a title card (a dissolve may borrow ``borrow`` s past the window)."""
    out = []
    for a, b in windows:
        for s0, s1 in KNOWN.get(int(video_id), {}).get('slates', []):
            if a < s1 and b + borrow > s0:
                out.append(f'{a}-{b} touches title card {s0}-{s1}')
    return out


def info(video_id: int) -> dict:
    meta = KNOWN.get(int(video_id))
    if meta is None:
        raise NoaaError(f'NOAA video {video_id} is not a reviewed B-roll package')
    return {'source': 'noaa', 'id': int(video_id), 'title': meta['title'], 'description': meta['description'],
            'author': 'NOAA Fisheries', 'license': LICENSE, 'license_url': LICENSE_URL,
            'page': PAGE.format(v=video_id), 'license_review_pending': False}


def download(client: httpx.Client, video_id: int, dest: Path) -> Path:
    info(video_id)
    url = DOWNLOAD.format(a=ACCOUNT, s=SITE, v=int(video_id))
    for _ in range(5):   # follow redirects by hand, only to Brightcove hosts
        with client.stream('GET', url, timeout=300, follow_redirects=False) as r:
            if r.status_code in (301, 302, 303, 307, 308):
                url = str(httpx.URL(url).join(r.headers['location']))
                if not _host_ok(url):
                    raise NoaaError('redirect to a host that is not allowed: ' + (urlparse(url).hostname or ''))
                continue
            if r.status_code != 200:
                raise NoaaError(f'download HTTP {r.status_code}')
            dest.parent.mkdir(parents=True, exist_ok=True)
            size = 0
            with dest.open('wb') as fh:
                for chunk in r.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise NoaaError('file too large')
                    fh.write(chunk)
            return dest
    raise NoaaError('too many redirects')
