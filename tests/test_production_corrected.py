"""Task 6 offline engineering tests; no network or real paid API."""
from pathlib import Path
import pytest
from pipeline.models import ScriptArtifact,ScriptSection,Scene,StoryboardOutput
from production import FakeTTSBackend, EspeakOfflineBackend, RenderConfig,render_video
from production.errors import RenderError,UnsafeVisualError
from production.captions import group_words
from production.models import WordTiming
from production.audio import normalize,loudness
from production.assets import card


def script():
    return ScriptArtifact(topic='engineering test',title='Workflow',hook='Here is the problem.',sections=[ScriptSection(heading='Problem',narration='A small company loses time handling invoices by hand.',on_screen_text='MANUAL WORK',claim_ids=[]),ScriptSection(heading='Concept',narration='A simple checklist can improve organization of customer tasks.',on_screen_text='WORKFLOW CONCEPT',claim_ids=[])],cta='Subscribe for the next walkthrough.',duration_s=15.,word_count=25,verified_at='2026-10-13T00:00:00+00:00')

def storyboard(kind2='diagram'):
    return StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=5,visual_type='diagram',instruction='Abstract checklist',claim_ids=[]),Scene(index=1,section_index=1,start_s=5,end_s=10,visual_type=kind2,instruction='Concept slide',claim_ids=[])])

def test_requires_review_approval(tmp_path):
    with pytest.raises(RenderError,match='approved'):
        render_video(script(),storyboard(),tmp_path/'video.mp4',FakeTTSBackend())

def test_cannot_fake_screen_recording(tmp_path):
    with pytest.raises(UnsafeVisualError):
        render_video(script(),storyboard('screen_recording'),tmp_path/'video.mp4',FakeTTSBackend(),approved=True)

def test_cannot_fabricate_numeric_chart(tmp_path):
    with pytest.raises(UnsafeVisualError):
        render_video(script(),storyboard('chart'),tmp_path/'video.mp4',FakeTTSBackend(),approved=True)

def test_caption_wraps_each_line():
    words=[WordTiming(text=f'word{i}',start_s=i*.22,end_s=(i+1)*.22) for i in range(28)]
    blocks=group_words(words,max_chars=18,max_lines=2)
    assert blocks
    for b in blocks:
        assert len(b['text'].split('\\N')) <= 2
        assert all(len(line)<=18 for line in b['text'].split('\\N'))

def test_word_too_long_fails():
    with pytest.raises(ValueError):
        group_words([WordTiming(text='x'*50,start_s=0,end_s=1)],max_chars=32)

def test_cards_do_not_create_fake_data(tmp_path):
    with pytest.raises(UnsafeVisualError):
        card('chart','Numbers','claimed growth',(480,270),tmp_path/'x.png')
    with pytest.raises(UnsafeVisualError):
        card('screen_recording','Fake','Demo',(480,270),tmp_path/'x.png')

def test_end_to_end_offline_tone(tmp_path):
    conf=RenderConfig(width=480,height=270,fps=12,crf=28,preset='ultrafast',caption_size=20,temp_scale=1)
    output=tmp_path/'demo.mp4'
    report=render_video(script(),storyboard(),output,FakeTTSBackend(),config=conf,workdir=tmp_path/'work',approved=True)
    assert report.width==480 and report.height==270
    assert report.scene_count==4 # hook + two sections + CTA
    assert report.caption_count>=4
    assert report.ready_for_publication is False
    assert report.tts_backend=='fake'
    assert 'TEST TONE' in str(report.warnings)
    assert output.exists() and output.stat().st_size > 3000
    assert abs(report.audio_lufs+16)<2

def test_voice_real_offline_when_espeak_present(tmp_path):
    import shutil
    if not shutil.which('espeak'): pytest.skip('espeak not installed')
    result=EspeakOfflineBackend().synthesize('This is a test of an offline voice.',tmp_path/'voice.wav')
    assert result.backend=='espeak-estimated'
    assert result.duration_s>1
    assert len(result.word_timings)==8
