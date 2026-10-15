from pathlib import Path
from unittest.mock import Mock
import subprocess,wave
import pytest
from narration_pro.narrator import PiperOrEdgeNarrator,NarrationError,SynthesisResult


def test_primary_success_never_contacts_online_fallback(tmp_path):
    result=object();primary=Mock();primary.synthesize.return_value=result;edge=Mock()
    engine=PiperOrEdgeNarrator(tmp_path/'voice',allow_edge_fallback=True,
        primary_factory=Mock(return_value=primary),edge_factory=edge)
    assert engine.synthesize('Original text',tmp_path/'out.wav') is result
    edge.assert_not_called();assert engine.actual_backends=={'piper'}


def test_fallback_requires_explicit_opt_in(tmp_path):
    edge=Mock();engine=PiperOrEdgeNarrator(tmp_path/'missing',edge_factory=edge)
    with pytest.raises(NarrationError):engine.synthesize('Original text',tmp_path/'out.wav')
    edge.assert_not_called()


def test_fallback_converts_actual_media_and_identifies_backend(tmp_path):
    # A test tone is only a codec fixture; not represented as actual voice.
    class FixtureEdge:
        def synthesize(self,text,path,voice):
            subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i',
                'sine=frequency=440:duration=0.5',str(path)],check=True,capture_output=True)
    engine=PiperOrEdgeNarrator(tmp_path/'missing',allow_edge_fallback=True,edge_factory=FixtureEdge)
    path=tmp_path/'out.wav';result=engine.synthesize('Original text',path)
    assert result.voice_model.startswith('edge:') and engine.actual_backends=={'edge-tts'}
    with wave.open(str(path)) as f:assert f.getframerate()==48000 and f.getnchannels()==1
    assert not path.with_suffix('.edge.mp3').exists()


def test_both_backends_fail_closed_without_placeholder_audio(tmp_path):
    edge=Mock();edge.synthesize.side_effect=RuntimeError('service unavailable')
    engine=PiperOrEdgeNarrator(tmp_path/'missing',allow_edge_fallback=True,edge_factory=lambda:edge)
    path=tmp_path/'out.wav'
    with pytest.raises(NarrationError,match='no substitute'):engine.synthesize('Original text',path)
    assert not path.exists() and not engine.actual_backends
