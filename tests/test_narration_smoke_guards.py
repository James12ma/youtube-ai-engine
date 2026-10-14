"""No model/network used. Verifies strict smoke quality gates and offline FFmpeg render."""
import json
from pathlib import Path
import pytest
from scripts.enforce_gates import (validate_alignment, validate_captions,
                                   parse_ass, enforce)
from scripts.narration_smoke import render, measure

WORDS=[{'word':s,'start_s':i*0.31,'end_s':i*0.31+0.24}
        for i,s in enumerate('Small teams can automate simple recurring tasks'.split())]
TRANSCRIPT='Small teams can automate simple recurring tasks'


def test_genuine_coverage_required():
    assert validate_alignment(TRANSCRIPT,WORDS,3)>0.98
    with pytest.raises(ValueError,match='Incomplete'):
        validate_alignment(TRANSCRIPT,WORDS[:3],3)


def test_timing_rejects_overlaps_and_bad_bounds():
    with pytest.raises(ValueError,match='Overlapping'):
        validate_alignment(TRANSCRIPT,[WORDS[0],dict(WORDS[1],start_s=.1),*WORDS[2:]],3)
    with pytest.raises(ValueError,match='timestamp'):
        validate_alignment(TRANSCRIPT,[dict(WORDS[0],start_s=-3)]+WORDS[1:],3)


def test_caption_text_and_timing_must_match():
    valid=[{'start':0,'end':2,'text':TRANSCRIPT,'lines':[TRANSCRIPT]}]
    with pytest.raises(ValueError,match='Captions omit'):
        validate_captions(WORDS,[dict(valid[0],text='Small teams can')],3)
    with pytest.raises(ValueError,match='Caption line'):
        validate_captions(WORDS,valid,3)
    wrapped=[{'start':0,'end':2,'text':TRANSCRIPT,
              'lines':['Small teams can automate','simple recurring tasks']}]
    assert validate_captions(WORDS,wrapped,3)==1


def test_zero_workflow_false_positive_blocked(tmp_path):
    # Fake a perfect self-report, but no material files: FAIL CLOSED.
    (tmp_path/'qc_report.json').write_text(json.dumps({
        'aligner_ran': True,'token_coverage':1,'final_lufs':-16}))
    with pytest.raises(ValueError,match='Missing'):
        enforce(tmp_path,do_probe=False)


def test_ass_dialogue_parser_requires_real_cues(tmp_path):
    ass=tmp_path/'caption.ass'
    ass.write_text('[Events]\nDialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,Small teams\\Ncan automate\n')
    parsed=parse_ass(ass)
    assert parsed[0]['text']=='Small teams can automate'
    assert parsed[0]['lines']==['Small teams','can automate']


def test_yaml_cannot_declare_optional_fake_aligner():
    from pathlib import Path
    import yaml
    y=yaml.load((Path(__file__).parent.parent/'.github/workflows/narration-smoke.yml').read_text(),Loader=yaml.BaseLoader)
    script=(Path(__file__).parent.parent/'scripts/narration_smoke.py').read_text()
    assert 'run_aligner' not in script
    assert 'run_aligner' not in str(y)
    assert y['on']['workflow_dispatch'] is not None
    assert 'contents' in y['permissions']

@pytest.mark.skipif(__import__('shutil').which('ffmpeg') is None,reason='ffmpeg unavailable')
def test_real_full_hd_mp4_render_with_synthetic_audio(tmp_path):
    """Really render H264/AAC in 1080p with synthetic tone; NOT neural speech."""
    import subprocess
    audio=tmp_path/'test.wav'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i',
                    'sine=frequency=220:duration=1.3:sample_rate=48000',
                    '-af','volume=0.12',str(audio)],check=True,capture_output=True)
    ass=tmp_path/'test.ass'
    ass.write_text('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n'
                   '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, '
                   'SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, '
                   'StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, '
                   'Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                   'Style: Default,DejaVu Sans,50,&H00FFFFFF,&H000000FF,&H00000000,'
                   '&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,60,1\n'
                   '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, '
                   'MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.05,'
                   '0:00:01.20,Default,,0,0,0,,Synthetic audio test\n')
    out=tmp_path/'tiny.mp4'
    info=render(audio,ass,out)
    assert out.is_file() and out.stat().st_size>3000
    assert any(s['codec_name']=='h264' for s in info['streams'])
    assert any(s['codec_name']=='aac' for s in info['streams'])
