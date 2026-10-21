"""What the Director may use: built-in scenes (with their params and cue names) and the custom-scene API.
This text is given to the planning model verbatim, so it is written for it."""
from __future__ import annotations

from .styles import PACKS

SCENES = {
    'character': {
        'use': 'people doing things in a place (story moments, reactions, someone using a phone, celebrating)',
        'params': "setting: office|home|city|none; cast: [{look: a|b|c|d (consistent per person across the video), x: 0-1000, pose, seated: bool}]",
        'cues': "pose:<i>:<stand|wave|phone|point|think|type|cheer|read>, say:<i> {text<=24 chars}, emote:<i>:<smile|surprise|neutral>, prop:<i> {icon}, walk:<i> {to: x, dur}",
    },
    'phone_app': {
        'use': 'someone using an app on a phone: filling a form, tapping a button, getting a confirmation or notification',
        'params': 'app, fields: [{label, value}] (<=4), button, success, success_detail, look',
        'cues': 'open, type:<i> {dur}, tap, success, notify {text}',
    },
    'transfer': {
        'use': 'something travelling between people/places/systems (message, payment, file, data, request)',
        'params': 'nodes: [{icon, label}] (2-4), item: {icon, label}',
        'cues': 'send:<a>-<b> {dur} (adjacent nodes), arrive:<i>, light:<i> (node appears)',
    },
    'inbox': {
        'use': 'someone at a desk receiving, opening, reading and deciding on items (applications, emails, orders, tickets)',
        'params': 'look, title, items: [{from, subject}], detail: {title, lines: [..<=5]}, buttons: [..<=2]',
        'cues': 'incoming:<i>, open:<i>, read, click:<j>, stamp {text}',
    },
    'ui': {
        'use': 'operating any software window with a mouse: settings, forms, menus, toggles (tutorial / demo feel)',
        'params': 'title, elements: [{id, type: heading|text|input|button|toggle|item, label, value}]',
        'cues': 'click:<id>, type:<id> {text, dur}, toggle:<id>',
    },
    'table': {
        'use': 'rows of records with a status: spreadsheets, logs, lists, checks passing or failing',
        'params': "columns: [..], rows: [[..]], status: ['OK'|'ERROR'|'CHECK'|''], title",
        'cues': 'row:<i>, status:<i> {value}, highlight:<i>, callout {text, row}',
    },
    'bars': {
        'use': 'comparing a few real, sourced numbers',
        'params': 'labels, values, unit, max', 'cues': 'grow {dur}, highlight:<i>',
    },
    'number': {
        'use': 'one important real number', 'params': 'value, prefix, suffix, label, decimals', 'cues': 'count {dur}',
    },
    'steps': {
        'use': 'an ordered process or checklist', 'params': 'items: [..<=5]', 'cues': 'step:<i>, done:<i>',
    },
    'icons': {
        'use': 'a few concepts/ideas/things introduced one by one', 'params': 'items: [{icon, label}] (<=6)', 'cues': 'pop:<i>, focus:<i>',
    },
    'compare': {
        'use': 'two sides: before/after, wrong/right, myth/fact', 'params': 'left/right: {title, icon, lines: [..<=4], tone: bad|good}',
        'cues': 'left, right, verdict {text}',
    },
    'question': {
        'use': 'end card asking viewers to comment', 'params': 'question, options: [two short words]', 'cues': 'options',
    },
    'title': {
        'use': 'a big statement on screen (hooks, chapter titles)', 'params': 'kicker, text, accent_words, icon', 'cues': '(none)',
    },
}

ICONS = ('phone laptop cloud building server envelope doc check cross bell money lock chart search person star clock '
         'spreadsheet robot globe').split()

CUSTOM_API = r"""
CUSTOM SCENES. When no built-in scene shows the idea well, set "scene": "custom" and write "code":
  function scene(S){ /* build once */ ...; return function(t){ /* t = seconds since shot start; redraw */ } }
Draw SVG inside S.root (a 1000x1000 box; layout "full" gives the whole frame S.W x S.H).
Helpers (S.A): el(tag, attrs, parent), g(parent), text(parent, x, y, str, attrs), icon(parent, name, cx, cy, size),
  person(parent, look) -> {root, update(t, {pose, prev, at, bubble, bubbleAt, emote})}, setting(parent, office|home|city),
  tf(el, x, y, scale, rotateDeg), op(el, opacity), set(el, attrs), clamp, lerp, prog(t, start, dur) -> 0..1,
  eOut, eInOut, back (easings), pulse(t, at, dur).
Timing: S.at('cueName') = when the narration says that cue's phrase (1e9 if absent); S.args('cueName'); S.dur.
Colours: S.theme.bg, ink, accent, accent2, danger, ok, muted, paper.
Rules: deterministic (no Math.random, Date, timers, fetch); everything depends only on t; stay inside the box;
text >= 28px; something must visibly change at every cue. Example:
  function scene(S){const A=S.A;const sun=A.el('circle',{cx:500,cy:800,r:120,fill:S.theme.accent},S.root);
    const lab=A.text(S.root,500,200,'Sunrise',{'font-size':64});
    return t=>{const p=A.eOut(A.prog(t,S.at('rise',0),1.5));A.set(sun,{cy:A.lerp(800,380,p)});A.op(lab,p)};}
"""


def prompt_catalog() -> str:
    lines = ['BUILT-IN SCENES (name: use | params | cue names):']
    for name, d in SCENES.items():
        lines.append(f"- {name}: {d['use']} | params: {d['params']} | cues: {d['cues']}")
    lines.append('ICONS: ' + ', '.join(ICONS))
    lines.append('STYLE PACKS: ' + ', '.join(PACKS))
    lines.append(CUSTOM_API.strip())
    return '\n'.join(lines)
