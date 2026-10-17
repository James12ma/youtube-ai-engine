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


def test_music_is_measurably_ducked_during_voice(tmp_path):
    import numpy as np
    import wave
    from production_pro.premium import mix_audio
    sr=48000;t=np.arange(sr*4)/sr
    def wav(path, values):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr)
            f.writeframes((values*32767).astype('<i2').tobytes())
    voice=tmp_path/'voice.wav';music=tmp_path/'music.wav';mixed=tmp_path/'mixed.wav'
    wav(voice,.2*np.sin(2*np.pi*260*t)*((t>=1)&(t<3)))
    wav(music,.2*np.sin(2*np.pi*440*t))
    mix_audio(voice,mixed,music=music,profile=QualityProfile('screen','en'))
    with wave.open(str(mixed),'rb') as f:
        audio=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2).mean(axis=1)/32767
    def bed_amplitude(start):
        a=audio[int(start*sr):int((start+.15)*sr)];time=np.arange(len(a))/sr
        return abs(np.mean(a*np.exp(-2j*np.pi*440*time)))
    assert bed_amplitude(1.6)<bed_amplitude(.75)*.7


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
