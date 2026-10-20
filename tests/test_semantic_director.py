import copy,json
from pathlib import Path
import pytest
from tiktok_motion.semantic_director import compile_script,bind_timeline,validate_film,GENRES,words
from tiktok_motion.premium_job import make_plan

SCRIPT=' '.join(s['narration'] for s in json.loads(Path('examples/hybrid_applicant_recruiter.json').read_text())['scenes'])

def timed_plan(tmp_path):
    p=make_plan({'script':SCRIPT,'visual_mode':'cinematic'},tmp_path)
    for s in p['scenes']:
        tokens=words(s['narration'])
        s.update(words=[{'text':w,'start':i*.22,'end':i*.22+.2} for i,w in enumerate(tokens)],durationFrames=round((len(tokens)*.22+1)*30))
    p['durationInFrames']=sum(s['durationFrames'] for s in p['scenes'])
    return bind_timeline(p)

@pytest.mark.parametrize('genre',sorted(GENRES))
def test_ordinary_script_is_exact_and_actions_are_concrete(genre):
    d=compile_script(SCRIPT,genre)
    assert d['ready'] and not d['missing_requirements']
    assert ' '.join(s['narration'] for s in d['scenes'])==SCRIPT
    assert [e['action'] for s in d['scenes'] for e in s['events']]==['establish','compose_send','transmit','receive','review','invite']
    assert d['world']['application']['id']=='APP-042'

@pytest.mark.parametrize('text',["A helicopter circles a city and detects a warm car.",SCRIPT.replace('travels','teleports'),SCRIPT.replace('open position','position paying 500 dollars')])
def test_unsupported_actions_and_unsourced_facts_do_not_become_cards(text):
    d=compile_script(text)
    assert not d['ready'] and d['missing_requirements']


def test_reordered_cause_is_blocked():
    d=compile_script(' '.join([s['narration'] for s in reversed(compile_script(SCRIPT)['scenes'])]))
    assert not d['ready']


def test_word_timing_controls_click_and_transition(tmp_path):
    p=timed_plan(tmp_path);shots=p['director']['shots']
    assert validate_film(p)['passed']
    send=shots[1];scene=p['scenes'][1]
    expected=next(w['start'] for w in scene['words'] if w['text']=='sends')
    assert send['action_frame']==send['narration_range'][0]+round(expected*30)
    assert shots[2]['transition']['continuity_object']=='phone'
    assert shots[2]['camera']['from'][2:]==shots[1]['camera']['to'][2:]
    assert len({s['location_id'] for s in shots})==3

@pytest.mark.parametrize('fault',['actor','recipient','source','blank','timing','static_repeat'])
def test_editorial_gate_catches_continuity_and_relevance_regressions(tmp_path,fault):
    p=timed_plan(tmp_path);shots=p['director']['shots']
    if fault=='actor':shots[0]['subjects'][0]['appearance_ref']='different-person'
    elif fault=='recipient':shots[3]['application_id']='WRONG-99'
    elif fault=='source':shots[2]['source_sentence']='A completely unrelated story.'
    elif fault=='blank':shots[4]['simulation_label']=''
    elif fault=='timing':shots[1]['action_frame']=shots[1]['to']+1
    else:shots[4]['action']='establish'
    assert not validate_film(p)['passed']


def test_missing_native_alignment_does_not_use_proportional_guess(tmp_path):
    p=timed_plan(tmp_path);p['scenes'][1]['words']=[]
    with pytest.raises(ValueError,match='Native word alignment'):bind_timeline(p)


def test_registry_is_not_shared_mutable_state():
    a=compile_script(SCRIPT);a['world']['candidate']['shirt']='pink'
    assert compile_script(SCRIPT)['world']['candidate']['shirt']!='pink'
