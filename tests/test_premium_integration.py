from pathlib import Path
from types import SimpleNamespace
import hashlib,json
import pytest
from tiktok_motion.premium_job import make_plan,validate_request,captions_from_tokens,narrate
from scripts.premium_private_job import fetch_request


def test_exact_script_is_bound_to_output_and_never_rewritten(tmp_path):
    text='My EXACT first sentence, stays here.\n\nMy second paragraph is also kept exactly as supplied.'
    plan=make_plan({'script':text},tmp_path)
    assert [s['narration'] for s in plan['scenes']]==text.split('\n\n')
    assert plan['source_sha256']==hashlib.sha256(text.encode()).hexdigest()
    assert plan['auto_publish'] is False and plan['requires_owner_approval'] is True
    assert not plan['narration_rewritten']

@pytest.mark.parametrize('data',[{'script':'A topic'},{'script':'x '*30,'language':'es'},{'script':'x '*30,'voice':'chatterbox'},{'script':'x '*30,'profile':'legacy'}])
def test_no_unapproved_fallback_for_bad_requests(data):
    with pytest.raises(ValueError):validate_request(data)


def test_native_caption_timing_uses_model_timestamps():
    words=[SimpleNamespace(text='Hello',start_ts=.2,end_ts=.6),SimpleNamespace(text='world.',start_ts=.8,end_ts=1.2)]
    cues=captions_from_tokens(words,2)
    assert cues==[{'start':2.2,'end':3.2,'text':'Hello world.'}]
    assert captions_from_tokens([SimpleNamespace(text='bad',start_ts=None,end_ts=None)])==[]


def test_script_hash_mismatch_stops_before_narration(monkeypatch):
    import scripts.premium_private_job as m
    import httpx
    data={'script':'These are the exact owner words for this meaningful test.','voice':'af_heart'}
    def handler(req):
        if req.url.path.endswith('/getFile'):return httpx.Response(200,json={'ok':True,'result':{'file_path':'documents/file.json'}})
        return httpx.Response(200,json=data)
    client=httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(m.httpx,'Client',lambda **kw:client)
    with pytest.raises(ValueError,match='hash mismatch'):fetch_request({'file_id':'private-id','source_sha256':'0'*64,'voice':'af_heart'},'TEST_TOKEN')


def test_download_error_never_contains_secret(monkeypatch):
    import scripts.premium_private_job as m
    class Client:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,*a,**kw):raise RuntimeError('https://api.telegram.org/botSECRET/getFile')
    monkeypatch.setattr(m.httpx,'Client',lambda **kw:Client())
    with pytest.raises(ValueError) as e:fetch_request({'file_id':'id'},'SECRET')
    assert 'SECRET' not in str(e.value)


def test_structure_and_freeform_directions_do_not_rewrite_spoken_text(tmp_path):
    source={'title':'An example','scenes':[{'narration':'Say these exact words.','on_screen':'EXACT','kind':'process','items':['Draft','Review'],'visual_notes':'Show a real desktop'}]}
    plan=make_plan({'script':json.dumps(source)},tmp_path)
    assert plan['scenes'][0]['narration']=='Say these exact words.'
    assert plan['visual_notes_require_review'] is True


def test_empty_native_timing_fails_instead_of_fake_alignment(tmp_path):
    import numpy as np
    def pipeline(*a,**kw):yield SimpleNamespace(audio=np.zeros(24000),tokens=[])
    with pytest.raises(ValueError,match='timing missing'):narrate({'voice':'af_heart','scenes':[{'narration':'Some words here.'}]},tmp_path,pipeline)


def test_caption_punctuation_and_contractions_stay_readable():
    tokens=[SimpleNamespace(text=w,start_ts=i*.1,end_ts=i*.1+.08) for i,w in enumerate(['Don',"'",'t','rush',',','prepare','.'])]
    assert captions_from_tokens(tokens)[0]['text']=="Don't rush, prepare."
