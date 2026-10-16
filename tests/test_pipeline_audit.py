"""Adversarial Task 4 acceptance tests."""
import hashlib
from types import SimpleNamespace
import pytest
import httpx
from pipeline.pipeline import ContentPipeline, QualityThresholds, _word_count
from pipeline.models import (Source, ClaimProposal, ResearchOutput, ScriptOutput, ScriptSection,
    ScriptArtifact, VerificationArtifact, VerifiedClaim, StoryboardOutput, Scene)
from pipeline.errors import PipelineQualityError
from pipeline.sources import HttpSourceFetcher
from tests import test_pipeline_offline as base

@pytest.fixture
def repo(tmp_path):
    return base._init_repo(tmp_path / "repo")

@pytest.fixture(autouse=True)
def authorize(monkeypatch):
    monkeypatch.setenv("ROUTER_ALLOW_LIVE_API", "1")

def test_claim_cannot_misquote_source_number():
    src=base._source('https://example.com/a','Company reported saving 4 hours per day.')
    p=ClaimProposal(text='Company saved 400 hours per day.',source_id=src.source_id,supporting_snippet='saving 4 hours per day')
    verified,rejected=ContentPipeline._verify_claims([p],[src])
    assert not verified and rejected

def test_short_script_is_not_eight_minute_video():
    output=ScriptOutput(title='Title',hook='Hook',sections=[ScriptSection(heading='Demo',narration='Only seven words in this short demo.',claim_ids=[])],cta='Subscribe')
    verified=VerificationArtifact(topic='t',verified=[],rejected=[],pass_rate=1.0,verified_at='2026-01-01T00:00:00+00:00')
    pipeline=object.__new__(ContentPipeline)
    pipeline._t=QualityThresholds()
    with pytest.raises(PipelineQualityError) as info:pipeline._validate_script(output,verified)
    assert 'duration' in info.value.report.get('reason','')

def test_storyboard_rejects_overlapping_scenes_even_if_total_matches():
    script=ScriptArtifact(topic='t',title='Title',hook='Hook',sections=[ScriptSection(heading='One',narration='Hi'),ScriptSection(heading='Two',narration='Hi')],cta='CTA',duration_s=30.,word_count=75,verified_at='2026-01-01T00:00:00+00:00')
    verified=VerificationArtifact(topic='t',verified=[],rejected=[],pass_rate=1.,verified_at='2026-01-01T00:00:00+00:00')
    scenes=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=15,visual_type='diagram',instruction='first'),Scene(index=1,section_index=1,start_s=0,end_s=15,visual_type='diagram',instruction='second')])
    p=object.__new__(ContentPipeline);p._t=QualityThresholds()
    with pytest.raises(PipelineQualityError):p._validate_storyboard(scenes,script,verified)

def test_numeric_hook_requires_evidence():
    output=ScriptOutput(title='Title',hook='Save $900 each month guaranteed.',sections=[ScriptSection(heading='Demo',narration='Here is a demo.')],cta='Subscribe')
    verified=VerificationArtifact(topic='t',verified=[],rejected=[],pass_rate=1.,verified_at='2026-01-01T00:00:00+00:00')
    p=object.__new__(ContentPipeline);p._t=QualityThresholds(min_script_duration_s=0)
    with pytest.raises(PipelineQualityError):p._validate_script(output,verified)

def test_reject_localhost_https_url_without_transport_call():
    calls=[]
    def handler(req):calls.append(req.url);return httpx.Response(200,text='<html>secret</html>')
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError):fetcher.fetch('https://127.0.0.1/private')
    assert calls==[]

def test_reject_redirect_to_insecure_scheme():
    calls=[]
    def handler(req):
        calls.append(str(req.url));return httpx.Response(302,headers={'Location':'http://127.0.0.1/internal'})
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(handler),follow_redirects=True),allowed_hosts={'example.com'})
    with pytest.raises(ValueError):fetcher.fetch('https://example.com/a')
    assert len(calls)==1

def test_source_html_does_not_promote_script_contents():
    html='<html><head><title>Test</title><script>FAKECLAIM: 9999%</script></head><body><main>Useful factual text</main></body></html>'
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200,text=html,headers={'Content-Type':'text/html'}))),allowed_hosts={'example.com'})
    source=fetcher.fetch('https://example.com/a')
    assert 'Useful factual text' in source.text
    assert 'FAKECLAIM' not in source.text

def test_source_change_invalidates_research_cache(repo):
    original, ids, script, storyboard = base._fixtures()
    fetcher1=base.FakeFetcher({u:base._source(u,base.SRC_TEXTS[u]) for u in base.SRC_URLS})
    first=base.QueuedAdapter('groq',[original,script,storyboard])
    base._pipeline(repo,first,fetcher1).run('AI automation for HVAC companies',base.SRC_URLS)
    # The same URLs now have changed factual contents; the additional claim
    # must produce a new research task rather than reusing cached research.
    revised=base.SRC_TEXTS.copy()
    revised[base.SRC_URLS[0]]+=' The company adopted a CRM in 2026.'
    fetcher2=base.FakeFetcher({u:base._source(u,revised[u]) for u in base.SRC_URLS})
    extra=ClaimProposal(text='The company adopted a CRM in 2026.',
                        source_id=base._source(base.SRC_URLS[0],'').source_id,
                        supporting_snippet='adopted a CRM in 2026')
    second_research=ResearchOutput(claims=[*original.claims,extra])
    second=base.QueuedAdapter('groq',[second_research,script,storyboard])
    result=base._pipeline(repo,second,fetcher2).run('AI automation for HVAC companies',base.SRC_URLS)
    assert second.calls==2  # research and script changed; storyboard script remained identical
    assert len(result.research.claims)==4
    assert result.stage_cache_hits==[]

def test_storyboard_cache_key_follows_actual_narration(repo):
    state=__import__('state_store').StateStore(repo,push_required=False)
    script_one=ScriptArtifact(topic='t',title='Same Title',hook='Hook',sections=[ScriptSection(heading='One',narration='Step one, then two.')],cta='CTA',duration_s=10,word_count=25,verified_at='2026-01-01T00:00:00+00:00')
    script_two=ScriptArtifact(topic='t',title='Same Title',hook='Hook',sections=[ScriptSection(heading='One',narration='Step three, then four.')],cta='CTA',duration_s=10,word_count=25,verified_at='2026-01-01T00:00:00+00:00')
    verified=VerificationArtifact(topic='t',verified=[],rejected=[],pass_rate=1,verified_at='2026-01-01T00:00:00+00:00')
    first=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=10,visual_type='diagram',instruction='first storyboard')])
    second=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=10,visual_type='diagram',instruction='second storyboard')])
    adapter=base.QueuedAdapter('groq',[first,second])
    from router import Router,RouterConfig
    p=ContentPipeline(state,Router(state,{'groq':adapter},RouterConfig(provider_order=('groq',))),base.FakeFetcher({}))
    assert p._stage_storyboard(script_one,verified,[]).scenes[0].instruction=='first storyboard'
    assert p._stage_storyboard(script_two,verified,[]).scenes[0].instruction=='second storyboard'
    assert adapter.calls==2

def test_source_limit_blocks_large_response():
    from pipeline.sources import MAX_BYTES
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(
        lambda req:httpx.Response(200,text='x'*(MAX_BYTES+1),headers={'Content-Type':'text/plain'}))),allowed_hosts={'example.com'})
    with pytest.raises(ValueError,match='Source (?:is too large|size limit)' ):
        fetcher.fetch('https://example.com/a')

def test_invalid_llm_research_can_recover_without_poisoned_router_cache(repo):
    valid, ids, script, storyboard=base._fixtures()
    bad=ResearchOutput(claims=[ClaimProposal(text='Claim with false number 9000',
        source_id=base._source(base.SRC_URLS[0],'').source_id,
        supporting_snippet='saved 4 hours per day')])
    adapter=base.QueuedAdapter('groq',[bad,valid,script,storyboard])
    state=__import__('state_store').StateStore(repo,push_required=False)
    from router import Router,RouterConfig
    pipeline=ContentPipeline(state,Router(state,{'groq':adapter},RouterConfig(provider_order=('groq',))),
        base.FakeFetcher({u:base._source(u,base.SRC_TEXTS[u]) for u in base.SRC_URLS}),
        QualityThresholds(min_script_duration_s=0,max_script_duration_s=1800,max_stage_revisions=2))
    result=pipeline.run('Automation',base.SRC_URLS)
    assert adapter.calls==4
    assert len(result.research.claims)==3
    assert result.verification.pass_rate==1

def test_script_quality_retries_revised_request(repo):
    valid,ids,good_script,storyboard=base._fixtures()
    bad_script=ScriptOutput(title='Short',hook='Hook',sections=[ScriptSection(heading='Empty',narration='Wrong claim $999',claim_ids=[])],cta='Subscribe')
    adapter=base.QueuedAdapter('groq',[valid,bad_script,good_script,storyboard])
    state=__import__('state_store').StateStore(repo,push_required=False)
    from router import Router,RouterConfig
    pipeline=ContentPipeline(state,Router(state,{'groq':adapter},RouterConfig(provider_order=('groq',))),
        base.FakeFetcher({u:base._source(u,base.SRC_TEXTS[u]) for u in base.SRC_URLS}),
        QualityThresholds(min_script_duration_s=0,max_script_duration_s=1800,max_stage_revisions=2))
    result=pipeline.run('Automation',base.SRC_URLS)
    assert adapter.calls==4
    assert result.script.title==good_script.title


def test_same_host_https_redirect_is_followed_and_provenance_kept():
    calls=[]
    def handler(req):
        calls.append(str(req.url))
        if req.url.path=='/es/a':return httpx.Response(301,headers={'Location':'/es/a/'})
        return httpx.Response(200,text='<html><title>T</title><main>Official text</main></html>',headers={'Content-Type':'text/html'})
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)),allowed_hosts={'www.irs.gov'})
    source=fetcher.fetch('https://www.irs.gov/es/a')
    assert calls==['https://www.irs.gov/es/a','https://www.irs.gov/es/a/'] and source.url=='https://www.irs.gov/es/a'


@pytest.mark.parametrize('location',['https://evil.example/x','http://www.irs.gov/es/a/','https://user:pw@www.irs.gov/x','https://www.irs.gov:8443/x','https://127.0.0.1/x'])
def test_unsafe_redirect_targets_rejected(location):
    calls=[]
    def handler(req):calls.append(str(req.url));return httpx.Response(302,headers={'Location':location})
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)),allowed_hosts={'www.irs.gov'})
    with pytest.raises(ValueError,match='Redirects are disabled'):fetcher.fetch('https://www.irs.gov/es/a')
    assert len(calls)==1


def test_same_host_redirect_chain_is_bounded():
    calls=[]
    def handler(req):
        calls.append(str(req.url));return httpx.Response(302,headers={'Location':'/hop'+str(len(calls))})
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)),allowed_hosts={'www.irs.gov'})
    with pytest.raises(ValueError,match='Redirects are disabled'):fetcher.fetch('https://www.irs.gov/start')
    assert len(calls)==4


def test_main_content_preferred_over_site_menus():
    menu=' '.join(['Menu']*500)
    body=' '.join(['Usted necesita un ITIN si tiene un proposito tributario federal.']*10)
    html=f'<html><title>T</title><body><div class="menu">{menu}</div><main><div><p>{body}</p><img src=x><br></div></main><div>after</div></body></html>'
    fetcher=HttpSourceFetcher(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200,text=html,headers={'Content-Type':'text/html'}))),allowed_hosts={'www.irs.gov'})
    text=fetcher.fetch('https://www.irs.gov/es/a').text
    assert text.startswith('Usted necesita') and 'Menu' not in text and 'after' not in text
