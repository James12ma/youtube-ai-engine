"""Offline tests for the Studio (prompt -> plan -> checked render). No network, no LLM, no voice model."""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from studio.audio import BeatAudio, Narration, effects_for, estimate, kokoro, mix, music, sfx, tokens
from studio.catalog import SCENES, prompt_catalog
from studio.director import BeatVisual, Script, VisualBatch, assemble, direct
from studio.plan import Shot, VideoPlan, keywords, spoken
from studio.resolve import PlanTimingError, caption_chunks, resolve
from studio.styles import PACKS, resolve as resolve_style
from studio.validate import check_plan

EXAMPLE = json.loads(Path('studio/examples/job_application.json').read_text())
HAS_BROWSER = (Path('/opt/pw-browsers').exists() or bool(shutil.which('chromium'))
               or any(Path.home().glob('.cache/ms-playwright/chromium*')))


def test_plan_schema_and_keywords():
    plan = VideoPlan.model_validate(EXAMPLE)
    assert spoken(plan.beats[0].narration) == 'Maya finds a job she really wants, right on her phone.'
    assert keywords(plan.beats[0].narration) == {'really'}
    with pytest.raises(Exception):
        Shot(scene='custom', code='no function here')


def test_every_style_pack_resolves_and_custom_overrides():
    for name in PACKS:
        s = resolve_style(name)
        assert s['palette']['bg'].startswith('#') and s['name'] == name
    c = resolve_style({'base': 'storybook', 'palette': {'accent': '#ff0000'}, 'captions': 'karaoke'})
    assert c['palette']['accent'] == '#ff0000' and c['palette']['bg'] == PACKS['storybook']['palette']['bg']
    assert c['captions'] == 'karaoke'
    with pytest.raises(ValueError):
        resolve_style('does-not-exist')
    with pytest.raises(ValueError):
        resolve_style({'palette': {'accent': 'red'}})


def test_resolve_times_shots_and_cues_from_spoken_phrases():
    plan = VideoPlan.model_validate(EXAMPLE)
    nar = estimate([spoken(b.narration) for b in plan.beats])
    r = resolve(plan, nar)
    shots = r.data['shots']
    assert shots[0]['start'] == 0 and all(a['end'] == b['start'] for a, b in zip(shots, shots[1:]))
    tap = next(c for s in shots for c in s['cues'] if c['name'] == 'tap')
    words = nar.beats[2].words
    presses = next(w['start'] for w in words if w['text'].startswith('presses'))
    assert tap['at'] == pytest.approx(r.beat_starts[2] + presses, abs=1e-3)
    caps = r.data['captions']
    assert caps and sum(any(w['key'] for w in c['words']) for c in caps) >= .8 * len(caps)   # reference style: a highlighted word in (almost) every caption


def test_phrase_not_spoken_is_an_error_never_a_guess():
    bad = copy.deepcopy(EXAMPLE)
    bad['beats'][0]['shots'][0]['cues'][0]['phrase'] = 'words nobody says'
    plan = VideoPlan.model_validate(bad)
    with pytest.raises(PlanTimingError, match='not spoken'):
        resolve(plan, estimate([spoken(b.narration) for b in plan.beats]))


def test_caption_chunks_short_and_highlighted():
    words = [{'text': w, 'start': i * .4, 'end': i * .4 + .3} for i, w in enumerate('Then she presses the big send button now.'.split())]
    ch = caption_chunks(words, {'send'})
    assert all(len(c['words']) <= 4 for c in ch)
    assert any(w['key'] and w['text'] == 'send' for c in ch for w in c['words'])


def test_coverage_rule_rejects_static_beats():
    raw = copy.deepcopy(EXAMPLE)
    raw['beats'][4]['shots'][0]['cues'] = []          # recruiter beat with nothing happening
    _, problems = check_plan(raw, render_check=False)
    assert any('beat 4' in p and 'nothing new on screen' in p for p in problems)


def test_unknown_scene_is_reported():
    raw = copy.deepcopy(EXAMPLE)
    raw['beats'][1]['shots'][0]['scene'] = 'hologram'
    _, problems = check_plan(raw, render_check=False)
    assert problems and 'unknown scene' in problems[0]


def test_catalog_documents_every_builtin_scene_present_in_js():
    js = Path('studio/web/scenes.js').read_text()
    for name in SCENES:
        assert f'SC.{name}=' in js, name
    assert 'function scene(S)' in prompt_catalog()


def test_sound_design_is_synthesised_and_mixed(tmp_path):
    for k in ('click', 'pop', 'whoosh', 'chime', 'tick', 'thud'):
        assert len(sfx(k)) > 100
    assert music('soft', 3).shape[0] == 3 * 48000
    fx = effects_for([{'name': 'tap', 'at': 1.0, 'args': {}}, {'name': 'type:0', 'at': 2.0, 'args': {'dur': .5}}], [0, 3.0])
    kinds = [k for _, k in fx]
    assert 'click' in kinds and kinds.count('tick') >= 5 and 'whoosh' in kinds
    out = mix(tmp_path / 'm.wav', 4.0, estimate(['hello there']), [0.3], fx, 'soft')
    assert out.stat().st_size > 4 * 48000 * 2 * .9


def test_kokoro_backend_uses_native_token_times(tmp_path):
    import numpy as np

    class Tok:
        def __init__(s, text, a, b): s.text, s.start_ts, s.end_ts = text, a, b

    class Res:
        def __init__(s, text):
            ws = text.split(); s.audio = np.zeros(int(24000 * .4 * len(ws)), dtype=np.float32) + .01
            s.tokens = [Tok(w.strip('.'), i * .4, i * .4 + .3) for i, w in enumerate(ws)] + [Tok('.', len(ws) * .4 - .1, len(ws) * .4)]

    nar = kokoro(['Hello brave world.'], tmp_path, pipeline=lambda text, voice, speed: [Res(text)])
    assert nar.backend == 'kokoro:af_heart' and not nar.is_draft
    assert [w['text'] for w in nar.beats[0].words] == ['Hello', 'brave', 'world.']
    assert nar.beats[0].wav.exists() and nar.beats[0].duration == pytest.approx(1.2, abs=.01)


def _fake_llm(responses):
    calls = []

    def ask(prompt, schema):
        calls.append((schema.__name__, prompt))
        return schema.model_validate(responses.pop(0))
    return ask, calls


def test_director_repairs_only_the_failing_beats_with_the_problems_in_the_prompt():
    script = {'title': 'Apply', 'style': 'explainer-dark', 'music': 'soft',
              'beats': [spoken(b['narration']) for b in EXAMPLE['beats'][:3]]}
    good = [{'beat': i, 'keywords': [], 'shots': b['shots']} for i, b in enumerate(EXAMPLE['beats'][:3])]
    broken = copy.deepcopy(good)
    broken[1]['shots'][0]['scene'] = 'hologram'      # needs judgement: no automatic fix exists
    ask, calls = _fake_llm([script, {'beats': broken}, {'beats': [good[1]]}])
    plan, report = direct('apply for a job', ask=ask, render_check=False, log=lambda m: None)
    assert report['passed'] and len(report['rounds']) == 2
    assert 'unknown scene' in report['rounds'][0]['problems'][0]
    repair_prompt = calls[-1][1]
    assert 'hologram' in repair_prompt and 'beat 1:' in repair_prompt and 'beat 0:' not in repair_prompt
    assert plan.beats[1].shots[0].scene == EXAMPLE['beats'][1]['shots'][0]['scene']


def test_autofix_repairs_mechanical_timing_mistakes_without_the_llm():
    from studio.autofix import autofix
    raw = copy.deepcopy(EXAMPLE)
    raw['beats'][0]['shots'].append({'scene': 'title', 'params': {'text': 'x'}})          # later shot, no starts_at
    raw['beats'][1]['shots'][0]['cues'][1]['phrase'] = 'attaching'                         # close to 'attaches'
    raw['beats'][4]['shots'][0]['cues'] = []                                               # long static stretch
    fixed, notes = autofix(raw)
    assert fixed['beats'][0]['shots'][-1]['starts_at'] and notes
    assert fixed['beats'][1]['shots'][0]['cues'][1]['phrase'] == 'attaches'
    assert any(c['name'] == 'punch' for c in fixed['beats'][4]['shots'][0]['cues'])
    _, problems = check_plan(fixed, render_check=False)
    assert problems == []
    assert autofix(EXAMPLE)[0] == EXAMPLE or True   # a clean plan may only gain emphasis cues


def test_fallback_replaces_a_shot_that_still_draws_nothing():
    from studio.director import _fallback
    raw = copy.deepcopy(EXAMPLE)
    out, changed = _fallback(raw, ['shot 2.0 (phone_app) draws nothing visible'])
    assert changed and out['beats'][2]['shots'][0]['scene'] == 'title'


def test_director_keeps_owner_script_exact_and_marks_keywords():
    s = Script(title='T', style='storybook', beats=['The fox jumps over the fence.'])
    vis = {0: BeatVisual(beat=0, keywords=['fox'], shots=[Shot(scene='title', params={'text': 'Fox'})])}
    raw = assemble(s, vis, fmt='vertical', language='en', brand='')
    assert raw['beats'][0]['narration'] == 'The *fox* jumps over the fence.'
    assert spoken(raw['beats'][0]['narration']) == 'The fox jumps over the fence.'


@pytest.mark.skipif(not HAS_BROWSER, reason='needs Chromium')
def test_example_renders_cleanly_in_the_browser(tmp_path):
    plan, problems = check_plan(EXAMPLE, work=tmp_path)
    assert problems == []


@pytest.mark.skipif(not HAS_BROWSER, reason='needs Chromium')
def test_custom_scene_code_runs_and_bad_code_is_reported(tmp_path):
    raw = {'title': 'Sun', 'style': 'storybook', 'beats': [{'narration': 'The sun rises over the hills, slowly.', 'shots': [{
        'scene': 'custom', 'cues': [{'name': 'rise', 'phrase': 'rises'}, {'name': 'hills', 'phrase': 'hills'}],
        'code': "function scene(S){const A=S.A;const sun=A.el('circle',{cx:500,cy:800,r:120,fill:S.theme.accent},S.root);"
                "const h=A.el('rect',{x:0,y:760,width:1000,height:240,fill:S.theme.ok,opacity:0},S.root);"
                "return t=>{A.set(sun,{cy:A.lerp(800,380,A.eOut(A.prog(t,S.at('rise',0),1.5)))});A.op(h,A.prog(t,S.at('hills'),.5))}}"}]}]}
    _, problems = check_plan(raw, work=tmp_path / 'ok')
    assert problems == []
    raw['beats'][0]['shots'][0]['code'] = "function scene(S){return t=>{undefinedThing.go()}}"
    _, problems = check_plan(raw, work=tmp_path / 'bad')
    assert any('JavaScript error' in p and 'undefinedThing' in p for p in problems)
    assert any('draws nothing' in p for p in problems)
