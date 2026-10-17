"""Voice packet compatibility tests only, not neural synthesis/naturalness claims."""
import hashlib
import json
import wave
import pytest
from narration_pro.prepared import PreparedNarrator
from narration_pro.narrator import NarrationError


def packet(tmp_path,language='en'):
    with wave.open(str(tmp_path/'beat_0.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\0\0'*24000)
    manifest={'engine':'fixture-not-a-real-voice','model':'fixture','language':language,
              'beats':[{'index':0,'sha1':hashlib.sha1(b'Test this cell.').hexdigest(),'seconds':1}]}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest));return manifest


def test_prepared_packet_reuses_exact_bytes_and_reports_actual_backend(tmp_path):
    packet(tmp_path);n=PreparedNarrator(tmp_path,language='en')
    r=n.synthesize('Test this cell.',tmp_path/'out.wav')
    assert r.duration_s==1 and (tmp_path/'out.wav').read_bytes()==(tmp_path/'beat_0.wav').read_bytes()
    assert n.actual_backends=={'fixture-not-a-real-voice'}
    with pytest.raises(NarrationError,match='few chapters'):n.synthesize('Test this cell.',tmp_path/'x.wav')


def test_mismatch_and_cross_language_audio_are_rejected(tmp_path):
    packet(tmp_path,'es')
    with pytest.raises(NarrationError,match='language'):PreparedNarrator(tmp_path,language='en')
    n=PreparedNarrator(tmp_path,language='es')
    with pytest.raises(NarrationError,match='text does not match'):n.synthesize('Different text.',tmp_path/'out.wav')


def test_audio_tampering_is_rejected_when_hash_supplied(tmp_path):
    manifest=packet(tmp_path);manifest['beats'][0]['audio_sha256']='0'*64
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    n=PreparedNarrator(tmp_path,language='en')
    with pytest.raises(NarrationError,match='hash mismatch'):n.synthesize('Test this cell.',tmp_path/'out.wav')
