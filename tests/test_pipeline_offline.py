"""Original eight tests for Task 4, recreated from the supplied cases."""
from __future__ import annotations
import hashlib, os, subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import pytest
from adapters import LLMRequest
from pipeline import (PUBLISHING_ENABLED,ContentPipeline,InsufficientSourcesError,PipelineQualityError,QualityThresholds,Source)
from pipeline.models import ClaimProposal,ResearchOutput,Scene,ScriptOutput,ScriptSection,StoryboardOutput
from router import Router,RouterConfig
from state_store import StateStore

def _init_repo(path):
    path.mkdir(parents=True,exist_ok=True)
    def run(*args):subprocess.run(['git',*args],cwd=path,check=True,capture_output=True)
    run('init','-b','main');run('config','user.email','t@e.i');run('config','user.name','T')
    (path/'.gitignore').write_text('.router-state/\n.router-locks/\n')
    (path/'README.md').write_text('seed\n')
    run('add','.gitignore','README.md');run('commit','-m','init')
    return path
@pytest.fixture
def repo(tmp_path):return _init_repo(tmp_path/'repo')
@pytest.fixture(autouse=True)
def _authorize(monkeypatch):monkeypatch.setenv('ROUTER_ALLOW_LIVE_API','1')
class QueuedAdapter:
    def __init__(self,name,queue,model='openai/gpt-oss-120b'):
        self.config=SimpleNamespace(name=name,default_model=model,max_retries=1)
        self._queue=list(queue);self.calls=0
    def complete(self,request):
        self.calls+=1
        if not self._queue:raise RuntimeError('QueuedAdapter exhausted')
        item=self._queue.pop(0)
        if isinstance(item,Exception):raise item
        return SimpleNamespace(parsed=item,text='',provider=self.config.name,model=self.config.default_model,usage={},raw={})
class FakeFetcher:
    def __init__(self,mapping):self._mapping=mapping
    def fetch(self,url):
        entry=self._mapping.get(url)
        if entry is None:raise RuntimeError('No fake source for '+url)
        if isinstance(entry,Exception):raise entry
        return entry
def _source(url,text,title='Doc'):
    return Source(source_id=hashlib.sha256(url.encode()).hexdigest()[:12],url=url,title=title,retrieved_at='2026-01-01T00:00:00+00:00',text=text)
def _pipeline(repo,adapter,fetcher):
    state=StateStore(repo,push_required=False)
    return ContentPipeline(state,Router(state,{'groq':adapter,'gemini':None,'openrouter':None},RouterConfig(provider_order=('groq',))),fetcher,QualityThresholds(min_script_duration_s=0,max_script_duration_s=1800,max_stage_revisions=1))
SRC_URLS=['https://example.com/a','https://example.com/b']
SRC_TEXTS={SRC_URLS[0]:'Acme HVAC reported that dispatch automation saved 4 hours per day for a three-person team in 2025.',SRC_URLS[1]:'Invoice automation reduced late payments by 30 percent for small contractors according to a 2024 survey.'}
def _research_output():
    return ResearchOutput(claims=[
        ClaimProposal(text='Dispatch automation saved 4 hours per day for a 3-person HVAC team.',source_id=_source(SRC_URLS[0],'').source_id,supporting_snippet='saved 4 hours per day'),
        ClaimProposal(text='Invoice automation reduced late payments by 30 percent for contractors.',source_id=_source(SRC_URLS[1],'').source_id,supporting_snippet='reduced late payments by 30 percent'),
        ClaimProposal(text='A three-person team was studied in 2025.',source_id=_source(SRC_URLS[0],'').source_id,supporting_snippet='three-person team in 2025')])
def _script_output(ids):
    return ScriptOutput(title='How HVAC Teams Automate Dispatch and Invoices',hook='Small HVAC teams lose hours to manual dispatch every week.',sections=[
        ScriptSection(heading='The Problem',narration='Manual scheduling consumes time. Dispatch automation saved 4 hours per day for a studied team.',on_screen_text='Manual dispatch is expensive',claim_ids=[ids[0]]),
        ScriptSection(heading='Invoices',narration='Late payments hurt cash flow. Invoice automation reduced late payments by 30 percent.',on_screen_text='Invoices that get paid',claim_ids=[ids[1]]),
        ScriptSection(heading='Team size',narration='The study tracked a small three-person team.',on_screen_text='Small team',claim_ids=[ids[2]])],cta='Subscribe to see the full build walkthrough.')
def _storyboard_output(ids,duration):
    per=duration/3
    return StoryboardOutput(scenes=[
        Scene(index=0,section_index=0,start_s=0,end_s=per,visual_type='diagram',instruction='Draw manual workflow',claim_ids=[ids[0]]),
        Scene(index=1,section_index=1,start_s=per,end_s=2*per,visual_type='screen_recording',instruction='Invoice tool demo.',claim_ids=[ids[1]]),
        Scene(index=2,section_index=2,start_s=2*per,end_s=3*per,visual_type='text_overlay',instruction='Team size statistic',claim_ids=[ids[2]])])
def _ids(research):
    from pipeline.pipeline import _claim_id
    return [_claim_id(c.text,c.source_id) for c in research.claims]
def _fixtures():
    research=_research_output();ids=_ids(research);script=_script_output(ids)
    from pipeline.pipeline import _word_count
    words=_word_count(script.hook,*[s.narration for s in script.sections],script.cta)
    duration=words/QualityThresholds().target_words_per_second
    return research,ids,script,_storyboard_output(ids,duration)
def test_happy_path_produces_all_artifacts(repo):
    research,ids,script,storyboard=_fixtures()
    fetcher=FakeFetcher({u:_source(u,SRC_TEXTS[u]) for u in SRC_URLS})
    adapter=QueuedAdapter('groq',[research,script,storyboard]);result=_pipeline(repo,adapter,fetcher).run('AI automation for HVAC companies',SRC_URLS)
    assert len(result.research.sources)==2 and len(result.verification.verified)==3
    assert result.verification.pass_rate==1 and result.script.title.startswith('How HVAC')
    assert len(result.storyboard.scenes)==3 and adapter.calls==3
def test_resume_skips_completed_stages(repo):
    research,ids,script,storyboard=_fixtures()
    fetcher=FakeFetcher({u:_source(u,SRC_TEXTS[u]) for u in SRC_URLS})
    a1=QueuedAdapter('groq',[research,script,storyboard]);_pipeline(repo,a1,fetcher).run('AI automation for HVAC companies',SRC_URLS)
    a2=QueuedAdapter('groq',[]);result=_pipeline(repo,a2,fetcher).run('AI automation for HVAC companies',SRC_URLS)
    assert a1.calls==3 and a2.calls==0 and set(result.stage_cache_hits)=={'research','verify','script','storyboard'}
def test_fabricated_snippet_rejected_and_threshold_enforced(repo):
    fetcher=FakeFetcher({u:_source(u,SRC_TEXTS[u]) for u in SRC_URLS})
    bad=ResearchOutput(claims=[ClaimProposal(text='Fabricated claim',source_id=_source(SRC_URLS[0],'').source_id,supporting_snippet='this text does not exist in the source'),ClaimProposal(text='Another fabricated claim',source_id=_source(SRC_URLS[1],'').source_id,supporting_snippet='also fabricated'),ClaimProposal(text='Real claim',source_id=_source(SRC_URLS[0],'').source_id,supporting_snippet='saved 4 hours per day')])
    with pytest.raises(PipelineQualityError) as ex:_pipeline(repo,QueuedAdapter('groq',[bad]),fetcher).run('topic',SRC_URLS)
    assert ex.value.stage=='research' and ex.value.report['verified']==1
def test_insufficient_sources(repo):
    fetcher=FakeFetcher({SRC_URLS[0]:_source(SRC_URLS[0],SRC_TEXTS[SRC_URLS[0]])})
    adapter=QueuedAdapter('groq',[])
    with pytest.raises(InsufficientSourcesError):_pipeline(repo,adapter,fetcher).run('topic',[SRC_URLS[0],'https://example.com/missing'])
    assert adapter.calls==0
def test_numeric_claim_without_citation_rejected(repo):
    fetcher=FakeFetcher({u:_source(u,SRC_TEXTS[u]) for u in SRC_URLS})
    bad=ScriptOutput(title='Short',hook='Hook',sections=[ScriptSection(heading='Numbers',narration='This saved 30% of time.',claim_ids=[])],cta='cta')
    with pytest.raises(PipelineQualityError) as ex:_pipeline(repo,QueuedAdapter('groq',[_research_output(),bad]),fetcher).run('topic',SRC_URLS)
    assert ex.value.stage=='script' and ex.value.report['reason']=='numeric claim without citation'
def test_unknown_claim_id_rejected(repo):
    fetcher=FakeFetcher({u:_source(u,SRC_TEXTS[u]) for u in SRC_URLS})
    bad=ScriptOutput(title='Title',hook='Hook',sections=[ScriptSection(heading='Heading',narration='Some narration.',claim_ids=['deadbeefdeadbeef'])],cta='cta')
    with pytest.raises(PipelineQualityError) as ex:_pipeline(repo,QueuedAdapter('groq',[_research_output(),bad]),fetcher).run('topic',SRC_URLS)
    assert ex.value.report['reason']=='unknown claim_id cited'
def test_storyboard_duration_drift_rejected(repo):
    research,ids,script,_=_fixtures()
    fetcher=FakeFetcher({u:_source(u,SRC_TEXTS[u]) for u in SRC_URLS})
    bad=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=1,visual_type='diagram',instruction='x',claim_ids=[])])
    with pytest.raises(PipelineQualityError) as ex:_pipeline(repo,QueuedAdapter('groq',[research,script,bad]),fetcher).run('topic',SRC_URLS)
    assert ex.value.stage=='storyboard' and ex.value.report['reason']=='duration drift exceeds tolerance'
def test_publishing_disabled():
    assert PUBLISHING_ENABLED is False and not hasattr(ContentPipeline,'publish')
    from pipeline import PublishingDisabledError
    assert issubclass(PublishingDisabledError,Exception)


def test_short_script_gate_reports_explicit_word_deficit(repo):
    research, ids, output, _ = _fixtures()
    pipe = _pipeline(repo, QueuedAdapter('groq',[]), FakeFetcher({}))
    pipe._t = QualityThresholds()
    from pipeline.models import VerificationArtifact, VerifiedClaim
    verification = VerificationArtifact(topic='test', verified=[VerifiedClaim(id=c,text='evidence',source_ids=['s'],supporting_snippets=['evidence']) for c in ids], rejected=[],pass_rate=1,verified_at='now')
    with pytest.raises(PipelineQualityError) as exc: pipe._validate_script(output, verification)
    assert exc.value.report['reason']=='duration outside 8-12 minute target'
    assert exc.value.report['min_words']==1200 and exc.value.report['max_words']==1800
    assert exc.value.report['word_count']<1200
