"""Failure boundaries; injected voice/alignment below are NOT real narration tests."""
import json
from types import SimpleNamespace
import httpx
import pytest
from pipeline.models import Scene, StoryboardOutput
from tests.test_channel_release import sample_artifacts
from scripts.check_research_pipeline import run, SOURCES


def sources():
    from tests.test_pipeline_offline import _source
    return SimpleNamespace(fetch=lambda url:_source(url,'Collect only necessary customer data and protect access.'))


def test_research_without_verified_free_account_never_generates(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','TEST_PRIVATE')
    called=[]
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'data':{'is_free_tier':False}}))) as client:
        report=run(tmp_path,metadata_client=client,source_fetcher=sources(),wire_factory=lambda **k:called.append(k))
    assert not called and not report['pipeline_passed'] and report['generation_requests']==0
    assert len(report['source_checks'])==2
    assert 'TEST_PRIVATE' not in (tmp_path/'report.json').read_text()


def test_research_rejects_paid_catalog_before_generation(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','TEST_PRIVATE')
    def metadata(request):
        return httpx.Response(200,json={'data':{'is_free_tier':True}} if request.url.path.endswith('/key')
            else {'data':[{'id':'model:free','pricing':{'prompt':'0','completion':'0.1'},'supported_parameters':['response_format']}]})
    called=[]
    with httpx.Client(transport=httpx.MockTransport(metadata)) as client:
        report=run(tmp_path,metadata_client=client,source_fetcher=sources(),wire_factory=lambda **k:called.append(k))
    assert not called and report['blocked']=='No verified zero-priced JSON model'


def test_source_failure_is_actionable_without_echoing_body_or_calling_ai(tmp_path):
    def fail(url): raise ValueError('Source is too large PRIVATE_BODY')
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(lambda r:calls.append(r))) as client:
        report=run(tmp_path,metadata_client=client,source_fetcher=SimpleNamespace(fetch=fail))
    assert not calls and report['generation_requests']==0
    assert all(s['reason']=='Source is too large' for s in report['source_checks'])
    assert 'PRIVATE_BODY' not in (tmp_path/'report.json').read_text()


def test_real_router_rate_limit_stops_source_pipeline_without_paid_failover(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','TEST_PRIVATE')
    monkeypatch.delenv('ENABLE_LIVE_LLM',raising=False)
    calls=[]
    def metadata(request):
        data={'is_free_tier':True,'free_model_daily_requests':{'remaining':1}} if request.url.path.endswith('/key') else [
            {'id':'model:free','pricing':{'prompt':'0','completion':'0'},'supported_parameters':['response_format']}]
        return httpx.Response(200,json={'data':data})
    def generation(request):
        calls.append(request)
        return httpx.Response(429,json={'error':{'message':'TEST_PRIVATE'}})
    with httpx.Client(transport=httpx.MockTransport(metadata)) as client:
        report=run(tmp_path,metadata_client=client,source_fetcher=sources(),
            wire_factory=lambda **kwargs:httpx.Client(transport=httpx.MockTransport(generation),**kwargs))
    assert len(calls)==1 and report['generation_requests']==1
    assert report['last_generation_http_status']==429 and not report['pipeline_passed']
    assert report['generation_requests_max']==1
    assert 'TEST_PRIVATE' not in (tmp_path/'report.json').read_text()
    assert 'ENABLE_LIVE_LLM' not in __import__('os').environ
    assert not (tmp_path/'metadata_draft.json').exists()


@pytest.mark.parametrize('passed',[False,True])
def test_renderer_propagates_qc_failure_and_keeps_diagnostic_report(tmp_path,monkeypatch,passed):
    import channel.video as video
    script,_,gate=sample_artifacts()
    storyboard=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=3,
        visual_type='text_overlay',instruction='Review')])
    class Dummy:
        def model_dump(self):return {'passed':passed}
    class Narrator:
        actual_backends={'TEST_FIXTURE'}
        def synthesize(self,text,path):return SimpleNamespace(wav_path=str(path),duration_s=1)
    monkeypatch.setattr(video,'PiperOrEdgeNarrator',lambda *a,**k:Narrator())
    monkeypatch.setattr(video,'_run',lambda *a:None)
    monkeypatch.setattr(video,'normalize_loudness',lambda *a:Dummy())
    aligned=SimpleNamespace(words=[],method='whisperx_ctc',token_coverage=1,duration_s=3)
    monkeypatch.setattr(video,'WhisperXAligner',lambda **k:SimpleNamespace(align=lambda *a:aligned))
    monkeypatch.setattr(video,'save_word_timestamps',lambda *a:None)
    monkeypatch.setattr(video,'build_ass_from_words',lambda *a,**k:(1,[{'start_s':0,'end_s':3,'words':['TEST FIXTURE']}]))
    monkeypatch.setattr(video,'assess_caption_quality',lambda *a,**k:SimpleNamespace(passed=True,model_dump=lambda:{}))
    monkeypatch.setattr(video,'card',lambda *a:None)
    monkeypatch.setattr(video,'compose_scenes',lambda *a,**k:{})
    monkeypatch.setattr(video,'burn_captions',lambda *a:None)
    qc=SimpleNamespace(passed=passed,model_dump=lambda:{'passed':passed,'failures':[] if passed else ['missing audio']})
    monkeypatch.setattr(video,'run_qc',lambda *a,**k:qc)
    if passed:
        assert video.render_approved_video(script,storyboard,gate,tmp_path/'voice',tmp_path/'out.mp4',reviewed=True)['technical_qc']['passed']
    else:
        with pytest.raises(video.VideoBuildError,match='technical QC'):
            video.render_approved_video(script,storyboard,gate,tmp_path/'voice',tmp_path/'out.mp4',reviewed=True)
    report=json.loads((tmp_path/'out_work/render_report.json').read_text())
    assert report['technical_qc']['passed'] is passed and not report['ready_for_publication']
    assert (tmp_path/'out.srt').is_file()


def test_production_srt_preserves_alignment_milliseconds_and_plain_words(tmp_path):
    from narration_pro import save_srt_from_blocks
    path=save_srt_from_blocks([{'start_s':.143,'end_s':1.207,'words':['Review','first.']}],tmp_path/'out.srt')
    assert '00:00:00,143 --> 00:00:01,207\nReview first.' in path.read_text()
    with pytest.raises(ValueError):
        save_srt_from_blocks([{'start_s':2,'end_s':1,'words':['Bad']}],tmp_path/'bad.srt')
    assert not (tmp_path/'bad.srt').exists()


def test_quality_diagnostic_preserves_exact_gate_but_redacts_generated_fields():
    from scripts.check_research_pipeline import safe_quality_failure
    from pipeline.errors import PipelineQualityError
    failure = PipelineQualityError('script', {'reason':'duration outside 8-12 minute target',
        'duration_s':310, 'word_count':775, 'section':'PRIVATE_SECRET', 'unknown':['PRIVATE_SECRET']})
    result = safe_quality_failure(failure)
    assert result['stage']=='script' and result['word_count']==775
    assert result['reason']=='duration outside 8-12 minute target'
    assert 'PRIVATE_SECRET' not in json.dumps(result)
    assert safe_quality_failure(PipelineQualityError('PRIVATE_SECRET', {'reason':'PRIVATE_SECRET'}))['reason']=='unclassified'
