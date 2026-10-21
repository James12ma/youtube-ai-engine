"""Style packs. A style is data, not code: palette, background, captions, headline and pacing.
The Director picks a pack by name or writes a new one (any field may be overridden)."""
from __future__ import annotations

import copy

BASE = {
    'palette': {'bg': '#0b1021', 'bg2': '#121a33', 'grid': '#141c38', 'ink': '#ffffff', 'muted': '#9fb3c8',
                'accent': '#f7bf75', 'accent2': '#7bf1d0', 'danger': '#ff5a5f', 'ok': '#22c55e',
                'paper': '#f8fafc', 'paperInk': '#0f172a', 'capbg': '#1c2233', 'capink': '#ffffff'},
    'background': 'grid',          # grid | paper | plain | glow
    'captions': 'box',             # box | karaoke | none
    'headline': True,
    'progress': True,
    'transition': 'push',          # push | slide | fade
    'transition_s': 0.32,
    'max_static_s': 2.8,           # QA: longest moment without visible change
    'music': 'soft',
}

PACKS = {
    # navy explainer with red/white pills and amber accent (bonnequestion-style "vrai ou faux")
    'explainer-dark': {},
    # white paper, red accent, black captions (bonnequestion light variant)
    'explainer-light': {'palette': {'bg': '#f4f2ee', 'bg2': '#ffffff', 'grid': '#e9e5de', 'ink': '#111111', 'muted': '#6b7280',
                                    'accent': '#dc2626', 'accent2': '#2563eb', 'capbg': '#2a2a2e'},
                        'background': 'paper'},
    # black, mono labels, green data accents (1pixeldesavoir-style data explainers)
    'data-minimal': {'palette': {'bg': '#0a0c0f', 'bg2': '#11151b', 'grid': '#0f1318', 'ink': '#e5e7eb', 'muted': '#6b7280',
                                 'accent': '#ff6b5a', 'accent2': '#34d399', 'capbg': '#151a21'},
                     'background': 'plain', 'headline': False, 'progress': False, 'transition': 'fade', 'music': 'pulse'},
    # near-black with orange accent and timeline feel (AI news explainers)
    'ai-dark': {'palette': {'bg': '#06070a', 'bg2': '#141824', 'grid': '#0b0d12', 'ink': '#f3f4f6', 'muted': '#8b93a7',
                            'accent': '#ff6a2b', 'accent2': '#a5b4fc', 'capbg': '#151821'},
                'background': 'glow', 'captions': 'karaoke', 'music': 'pulse'},
    # screen demo: neutral, captions low, no headline (tutorials over UI)
    'screen-demo': {'palette': {'bg': '#0f172a', 'bg2': '#1e293b', 'grid': '#0f172a', 'accent': '#facc15', 'accent2': '#38bdf8'},
                    'background': 'plain', 'headline': True, 'transition': 'slide'},
    # warm, playful (children / stories)
    'storybook': {'palette': {'bg': '#fff7e6', 'bg2': '#ffe8c2', 'grid': '#fff1d6', 'ink': '#3b2412', 'muted': '#8a6b4f',
                              'accent': '#f97316', 'accent2': '#0ea5e9', 'capbg': '#3b2412'},
                  'background': 'paper', 'music': 'playful'},
}


def resolve(style: str | dict) -> dict:
    """Return a complete style dict from a pack name or a partial dict (optionally with 'base')."""
    if isinstance(style, str):
        if style not in PACKS:
            raise ValueError(f'unknown style pack {style!r}; known: {sorted(PACKS)}')
        over, base = PACKS[style], style
    else:
        over = dict(style)
        base = over.pop('base', 'explainer-dark')
        if base not in PACKS:
            raise ValueError(f'unknown base pack {base!r}')
        over = _merge(copy.deepcopy(PACKS[base]), over)
    out = _merge(copy.deepcopy(BASE), copy.deepcopy(over))
    out['name'] = base if isinstance(style, str) else 'custom:' + base
    for k, v in out['palette'].items():
        if not (isinstance(v, str) and v.startswith('#') and len(v) in (4, 7, 9)):
            raise ValueError(f'palette colour {k} must be a hex colour')
    return out


def _merge(a: dict, b: dict) -> dict:
    for k, v in b.items():
        a[k] = _merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a
