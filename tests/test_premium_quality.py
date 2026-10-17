"""Render real FFmpeg media; verify fail-closed final and mode-specific evidence."""
import subprocess
from pathlib import Path
import pytest
from production_pro.premium import QualityProfile, master_video, local_narrator, audit_video


def test_final_refuses_small_picture_and_invalid_profile(tmp_path):
    with pytest.raises(ValueError, match='1080p'):
        QualityProfile('screen', 'en', width=1280, height=720)
    with pytest.raises(ValueError, match='mode/language'):
        QualityProfile('other', 'en')
    picture=tmp_path/'small.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=24:duration=1',
                    '-c:v','libx264','-preset','ultrafast',str(picture)],check=True)
    with pytest.raises(ValueError,match='native resolution'):
        master_video(picture,tmp_path/'absent.wav',tmp_path/'out.mp4',profile=QualityProfile('screen','en'))


def test_voice_language_mismatch_fails_before_loading_model(tmp_path):
    model=tmp_path/'model.onnx'
    Path(str(model)+'.json').write_text('{"language":{"code":"es_MX"}}')
    with pytest.raises(ValueError,match='language'):
        local_narrator(model,QualityProfile('screen','en'))


def test_mastering_decodes_both_modes_and_rejects_missing_evidence(tmp_path):
    src=tmp_path/'source.mp4';voice=tmp_path/'voice.wav';music=tmp_path/'bed.wav'
    def run(args):subprocess.run(['ffmpeg','-y','-v','error',*args],check=True)
    run(['-f','lavfi','-i','testsrc2=size=1920x1080:rate=24:duration=3',
         '-c:v','libx264','-preset','ultrafast',str(src)])
    run(['-f','lavfi','-i','sine=frequency=260:duration=3','-af',
         "volume='if(between(t,0.7,2.0),1,0)':eval=frame",str(voice)])
    run(['-f','lavfi','-i','sine=frequency=440:duration=3',str(music)])
    for mode in ('screen','documentary'):
        profile=QualityProfile(mode,'en' if mode=='screen' else 'es')
        out=tmp_path/(mode+'.mp4')
        report=master_video(src,voice,out,profile=profile,music=music)
        assert report['technical_passed'] and report['decode_passed']
        assert report['mode_evidence'] is None  # a good encode is not proof of a tutorial/wildlife scene
        assert report['audio_mix']['sidechain_ducking']
        assert not report['ready_for_publication']
    screen=audit_video(tmp_path/'screen.mp4',profile=QualityProfile('screen','en'),
                       screen_actions=[{'action':{'do':'set','expect':{'Sheet!A1':'5'}},'observed':{'Sheet!A1':'5'}}])
    assert not screen['mode_evidence']['passed'] and 'type' in screen['mode_evidence']['missing_interactions']
    documentary=audit_video(tmp_path/'documentary.mp4',profile=QualityProfile('documentary','es'),
                            documentary_report={'shots':[{'clip':'test'}]})
    assert not documentary['mode_evidence']['passed']  # semantic visual QA still absent
