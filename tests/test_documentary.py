import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from channel.documentary import (AI_LABEL, DocumentaryError, DocumentaryPlan, Shot, allocate, credit_lines,
                                 load_plan, spoken_text, timeline)

PLAN = Path(__file__).resolve().parents[1] / 'plans' / 'humpback_poc.json'


def _plan(**over):
    base = {'series': 'S', 'title': 'T', 'clips': {'a': {'title': 'File:A.webm'}},
            'beats': [{'narration': 'Uno dos tres.', 'shots': [{'clip': 'a', 'in_s': 0, 'out_s': 20}]}]}
    base.update(over)
    return DocumentaryPlan.model_validate(base)


@pytest.mark.parametrize('name', ['humpback_poc.json', 'humpback_poc2.json'])
def test_poc_plan_is_valid_and_fits_45_to_60_seconds(name):
    plan = load_plan(PLAN.parent / name)
    assert all(c.kind == 'commons' and not c.ai_generated for c in plan.clips.values())
    # Piper es_MX speaks roughly 2.2-2.8 words/s; the sample must stay in 45-60 s either way.
    for wps in (2.2, 2.8):
        t = timeline(plan, [len(b.narration.split()) / wps for b in plan.beats])
        assert 45 <= t['total_s'] <= 62
    # Every shot carries an on-screen location label.
    assert all(s.label for b in plan.beats for s in b.shots)


def test_unknown_clip_rejected():
    with pytest.raises(ValidationError):
        _plan(beats=[{'narration': 'x', 'shots': [{'clip': 'zzz', 'in_s': 0, 'out_s': 5}]}])


def test_commons_clip_cannot_be_marked_ai_and_ai_clip_needs_flag():
    with pytest.raises(ValidationError):
        _plan(clips={'a': {'title': 'File:A.webm', 'ai_generated': True}})
    with pytest.raises(ValidationError):
        _plan(clips={'a': {'kind': 'ai', 'path': 'x.mp4'}})
    p = _plan(clips={'a': {'kind': 'ai', 'path': 'x.mp4', 'ai_generated': True}})
    assert p.clips['a'].disclosure == AI_LABEL


def test_allocate_never_stretches_footage():
    shots = [Shot(clip='a', in_s=0, out_s=4), Shot(clip='a', in_s=10, out_s=16)]
    assert allocate(5, shots) == pytest.approx([2.0, 3.0])
    with pytest.raises(DocumentaryError):
        allocate(11, shots)


def test_timeline_totals():
    p = _plan(preroll_s=2, pause_s=0.5, tail_s=1, credits_s=5)
    t = timeline(p, [4.0])
    assert t['narration_starts'] == [2]
    assert sum(s['seconds'] for s in t['shots']) == pytest.approx(t['footage_s']) == pytest.approx(7.0)
    assert t['total_s'] == pytest.approx(12.0)


def test_credit_lines_state_licence_changes_and_ambience_origin():
    lines = credit_lines({'a': {'title': 'File:Whale.webm', 'author': 'Ann', 'license': 'CC BY 3.0',
                                'license_url': 'https://creativecommons.org/licenses/by/3.0'},
                          'b': {'title': 'gen.mp4', 'ai_generated': True}},
                         {'title': 'File:Waves.ogg', 'author': 'Bob', 'license': 'CC0'}, 'Voz: Piper')
    assert 'Ann' in lines[0] and 'CC BY 3.0' in lines[0] and 'recortado' in lines[0]
    assert AI_LABEL in lines[1] and 'gen.mp4' not in lines[1]
    assert 'No fue grabado' in lines[2]
    assert lines[-1] == 'Voz: Piper'


def test_spoken_text_only_swaps_whole_words():
    p = {'frías': 'fɾˈias', 'crías': 'kɾˈias', 'cría': 'kɾˈia'}
    assert spoken_text('aguas frías, sus crías y su cría; criadero', p) == \
        'aguas [[ fɾˈias ]], sus [[ kɾˈias ]] y su [[ kɾˈia ]]; criadero'


def test_segment_start_places_key_action_inside_cut():
    from channel.documentary import segment_start
    s = Shot(clip='a', in_s=100, out_s=120, key_s=115)
    start = segment_start(s, 5)
    assert start <= 115 <= start + 5 and start + 5 <= 120.6
    assert segment_start(Shot(clip='a', in_s=0, out_s=10), 4) == 0
    with pytest.raises(ValidationError):
        Shot(clip='a', in_s=0, out_s=10, key_s=12)
