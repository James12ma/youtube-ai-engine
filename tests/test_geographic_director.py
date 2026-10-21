import copy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from tiktok_motion.geographic_director import validate_geography, compile_geographic_scene
from tiktok_motion.premium_job import validate_clip_duration
from tiktok_motion.story_scene import enrich_visual

SPEC = json.loads((Path(__file__).parents[1]/'examples/god_eye_atlantic.json').read_text())

def test_geographic_story_reaches_existing_scene_grammar():
    scene = compile_geographic_scene(SPEC, 'atlantic')
    assert enrich_visual(scene)['geo_storyboard'] == SPEC
    assert scene['narration'] == SPEC['narration']

@pytest.mark.parametrize('coordinate', [float('nan'), float('inf'), True, 181, '18'])
def test_invalid_coordinates_block_capture(coordinate):
    spec=copy.deepcopy(SPEC);spec['route'][0]['lon']=coordinate
    with pytest.raises(ValueError):validate_geography(spec)

def test_no_invented_route_facts():
    spec={**SPEC,'illustrative':False}
    with pytest.raises(ValueError,match='evidence'):validate_geography(spec)

def test_cues_must_bind_to_narration():
    spec=copy.deepcopy(SPEC);spec['cues'][1]['phrase']='A whale breaches'
    with pytest.raises(ValueError,match='exact narration'):validate_geography(spec)

def test_scene_and_storyboard_cannot_disagree():
    scene=compile_geographic_scene(SPEC,'atlantic');scene['narration']='The ocean route leads somewhere else.'
    with pytest.raises(ValueError,match='mismatch'):enrich_visual(scene)

@pytest.mark.parametrize('duration', [0, 2, float('nan')])
def test_short_or_invalid_clips_cannot_freeze_under_speech(duration):
    with patch('subprocess.check_output',return_value=json.dumps({'format':{'duration':duration}})):
        with pytest.raises(ValueError,match='shorter'):validate_clip_duration(Path('clip.mp4'),12)

def test_exact_clip_duration_is_accepted():
    with patch('subprocess.check_output',return_value='{"format":{"duration":12}}'):
        assert validate_clip_duration(Path('clip.mp4'),12)==12

def test_semantic_director_preserves_exact_spatial_script():
    from tiktok_motion.semantic_director import compile_geographic_script
    director=compile_geographic_script(SPEC['narration'],SPEC)
    assert director['ready'] and director['scenes'][0]['kind']=='god_eye'
    with pytest.raises(ValueError,match='exact owner script'):
        compile_geographic_script('A different ocean journey.',SPEC)
