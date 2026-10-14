"""Task 8 offline tests. No API keys, model downloads, or network."""
import json,sys,types,wave,subprocess,shutil,math
from pathlib import Path
import pytest
from narration_pro import (PiperNarrator, NarrationError, WhisperXAligner,
    AlignmentError,WordTimestamp,build_ass_from_words,assess_caption_quality,normalize_loudness)


def wav(path:Path, seconds=2):
    import struct
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        f.writeframes(b'\0\0'*int(seconds*16000))
    return path

class FakeConfig:
    def __init__(self, **kwargs): self.kwargs=kwargs
class FakePiperVoice:
    def synthesize_wav(self,text,out,syn_config=None):
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000)
        out.writeframes(b'\x00\x00'*32000)

@pytest.fixture
def fake_piper(monkeypatch):
    piper=types.ModuleType('piper');piper.SynthesisConfig=FakeConfig
    monkeypatch.setitem(sys.modules,'piper',piper)

def test_piper_real_wav_structure_with_injected_voice(fake_piper,tmp_path):
    synth=PiperNarrator(tmp_path/'voice.onnx',voice=FakePiperVoice())
    result=synth.synthesize('The budget is approved.',tmp_path/'out.wav')
    assert result.duration_s==2 and result.sample_rate==16000
    assert Path(result.wav_path).stat().st_size>64000

def test_piper_rejects_empty_text(fake_piper,tmp_path):
    synth=PiperNarrator(tmp_path/'voice.onnx',voice=FakePiperVoice())
    with pytest.raises(NarrationError): synth.synthesize(' ',tmp_path/'out.wav')

def test_piper_requires_voice_config(tmp_path):
    (tmp_path/'voice.onnx').write_text('fake')
    with pytest.raises(NarrationError,match='json'): PiperNarrator(tmp_path/'voice.onnx')

class AlignerBackend:
    def __init__(self, word_items): self.items=word_items
    def load_align_model(self, **kwargs): return 'dummy-model',{'model_name':'test_ctc'}
    def load_audio(self,path): return b'audio'
    def align(self,*args,**kwargs): return {'segments':[{'words':self.items}]}

def test_aligner_genuine_backend_contract(tmp_path):
    audio=wav(tmp_path/'test.wav')
    items=[{'word':'Hello','start':0.1,'end':0.6,'score':0.9},
           {'word':'world.','start':0.7,'end':1.2,'score':0.9}]
    result=WhisperXAligner(backend=AlignerBackend(items)).align(audio,'Hello world.')
    assert result.method=='whisperx_ctc' and result.token_coverage==1
    assert result.alignment_model=='test_ctc' and result.words[1].end_s==1.2

def test_aligner_rejects_omitted_words(tmp_path):
    audio=wav(tmp_path/'test.wav')
    items=[{'word':'Hello','start':0,'end':0.5}]
    with pytest.raises(AlignmentError,match='incomplete'):
        WhisperXAligner(backend=AlignerBackend(items)).align(audio,'Hello world again')

def test_aligner_rejects_nonmonotonic_audio(tmp_path):
    audio=wav(tmp_path/'test.wav')
    items=[{'word':'hello','start':0.5,'end':1.5}, {'word':'world','start':0.6,'end':1.1}]
    with pytest.raises(AlignmentError,match='nonmonotonic'):
        WhisperXAligner(backend=AlignerBackend(items)).align(audio,'hello world')

def test_aligner_rejects_outside_audio(tmp_path):
    audio=wav(tmp_path/'test.wav')
    with pytest.raises(AlignmentError,match='interval'):
        WhisperXAligner(backend=AlignerBackend([{'word':'hello','start':1,'end':4}])).align(audio,'hello')

def test_caption_two_lines_and_qc(tmp_path):
    tokens='This narration is a clear sample that requires readable captions at ordinary viewing size'.split()
    words=[WordTimestamp(word=w,start_s=0.25*i,end_s=0.25*i+0.2) for i,w in enumerate(tokens)]
    n,blocks=build_ass_from_words(words,tmp_path/'captions.ass',width=1920,height=1080,max_chars_per_line=18)
    for b in blocks:
        assert all(len(line)<=18 for line in b['text'].split('\\N'))
        assert len(b['text'].split('\\N'))<=2
    assert n>=3
    qc=assess_caption_quality(words,blocks,5.0)
    assert qc.passed and qc.coverage_ratio==1
    assert '\\N' in (tmp_path/'captions.ass').read_text()

def test_caption_rejects_long_unbreakable_word(tmp_path):
    w=[WordTimestamp(word='W'*40,start_s=0,end_s=1)]
    with pytest.raises(ValueError):build_ass_from_words(w,tmp_path/'bad.ass',width=1080,height=1920)

def test_caption_detects_missing_text(tmp_path):
    words=[WordTimestamp(word='hello',start_s=0,end_s=0.3),WordTimestamp(word='world',start_s=0.4,end_s=0.7)]
    blocks=[dict(start_s=0,end_s=0.3,text='hello',words=['hello'])]
    qc=assess_caption_quality(words,blocks,1)
    assert not qc.passed and qc.text_match_ratio==0

def test_caption_does_not_punish_legitimate_long_pauses(tmp_path):
    words=[WordTimestamp(word='hello',start_s=0,end_s=0.3),WordTimestamp(word='world',start_s=2,end_s=2.3)]
    n,b=build_ass_from_words(words,tmp_path/'pauses.ass',width=1920,height=1080)
    assert assess_caption_quality(words,b,3).passed

@pytest.mark.skipif(shutil.which('ffmpeg') is None,reason='ffmpeg unavailable')
def test_real_ffmpeg_normalization(tmp_path):
    raw=tmp_path/'quiet.wav'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i','sine=frequency=220:duration=3:sample_rate=48000','-af','volume=0.05',str(raw)],check=True)
    report=normalize_loudness(raw,tmp_path/'norm.wav')
    assert -17.5 <= report.output_lufs <= -14.5
    assert report.output_true_peak <= -1.2
    assert report.gain_applied_lu>0

@pytest.mark.skipif(shutil.which('ffmpeg') is None,reason='ffmpeg unavailable')
def test_silent_wav_cannot_be_normalized(tmp_path):
    raw=wav(tmp_path/'silent.wav')
    with pytest.raises(RuntimeError): normalize_loudness(raw,tmp_path/'norm.wav')
