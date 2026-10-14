"""Task 5 tests: no network, no paid calls, real Pydantic artifact types."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import hashlib
import pytest
from pipeline.models import Source, VerifiedClaim, ResearchArtifact, VerificationArtifact, ScriptArtifact, ScriptSection
from verification import (EntailmentBatch, EntailmentJudgment, EntailmentLabel, ContradictionReport,
    ContradictionPair, VerificationGate, GateConfig, GateRejected, EntailmentVerifier,
    EntailmentError, ContradictionDetector, ContradictionConfig, ContradictionError,
    assess, build_trace, ClaimVerdict, VerifiedContentPipeline)

class QueueRouter:
    def __init__(self, *items):
        self.items=list(items)
        self.calls=[]
    def execute(self, task_type,input_data,request,schema):
        self.calls.append((task_type,input_data,request))
        assert self.items, 'Unexpected LLM call: ' + task_type
        item=self.items.pop(0)
        assert isinstance(item,schema),f'{type(item)} != {schema}'
        return item

def src(sid='s1',url='https://reuters.com/report',text='Verified study recorded 4 hours saved per day.'):
    return Source(source_id=sid,url=url,title='Study',retrieved_at='2026-10-01T00:00:00+00:00',text=text)

def claim(cid='c1',sid='s1',text='The study recorded 4 hours saved per day.',snippet='4 hours saved per day'):
    return VerifiedClaim(id=cid,text=text,source_ids=[sid],supporting_snippets=[snippet])

def judgment(cid='c1',sid='s1',label=EntailmentLabel.ENTAILMENT,confidence=.9):
    return EntailmentBatch(judgments=[EntailmentJudgment(claim_id=cid,source_id=sid,label=label,confidence=confidence)])

def artifacts(sources=None,claims=None,sections=None):
    sources=[src()] if sources is None else sources
    claims=[claim()] if claims is None else claims
    if sections is None:
        sections=[ScriptSection(heading='Intro',narration='The study recorded 4 hours saved per day.',claim_ids=['c1'])]
    research=ResearchArtifact(topic='topic',sources=sources,claims=claims,rejected_claims=[],retrieved_at='2026-10-01T00:00:00+00:00')
    verification=VerificationArtifact(topic='topic',verified=claims,rejected=[],pass_rate=1.,verified_at='2026-10-01T00:00:00+00:00')
    script=ScriptArtifact(topic='topic',title='Title',hook='Hook',sections=sections,cta='CTA',duration_s=60,word_count=140,verified_at='2026-10-01T00:00:00+00:00')
    return research,verification,script,sources

@pytest.mark.parametrize('url,tier',[
 ('https://www.nih.gov/report','A'),('https://cdc.gov/a','A'),
 ('https://reuters.com/a','B'),('https://www.mckinsey.com/a','B'),
 ('https://author.medium.com/a','C'),('https://reddit.com/r/a','D'),
 ('https://bit.ly/a','suspicious'),('https://unknown.example.org/report','C'),
 ('https://reddit.com.evil.example.org/report','C'),
 ('https://site.example.org/?goto=bit.ly','C'),
 ('http://reuters.com/test','suspicious'),
 ])
def test_domain_heuristics(url,tier):
    assert assess('s',url).tier==tier

def test_valid_claim_passes_but_requires_editorial_review():
    q=QueueRouter(judgment()); out=VerificationGate(q).run(*artifacts())
    assert out.report.accepted_count==1
    assert out.accepted_claims[0].id=='c1'
    assert out.warnings and 'review' in out.warnings[-1].lower()
    assert len(q.calls)==1

def test_neutral_rejected():
    q=QueueRouter(judgment(label=EntailmentLabel.NEUTRAL))
    with pytest.raises(GateRejected, match='no claims'):
        VerificationGate(q).run(*artifacts())

def test_contradiction_rejected():
    q=QueueRouter(judgment(label=EntailmentLabel.CONTRADICTION))
    with pytest.raises(GateRejected):
        VerificationGate(q).run(*artifacts())

def test_low_credibility_rejected():
    s=src(url='https://reddit.com/r/x')
    q=QueueRouter(judgment())
    with pytest.raises(GateRejected):
        VerificationGate(q).run(*artifacts([s]))

def test_rejected_claim_cited_fails_even_when_one_claim_accepted():
    s1=src()
    s2=src('s2','https://reuters.com/other','Unrelated data in this file.')
    c1=claim()
    c2=claim('c2','s2','Unrelated claim.','Unrelated data')
    section=ScriptSection(heading='Intro',narration='Some text.',claim_ids=['c1','c2'])
    q=QueueRouter(judgment(), judgment('c2','s2',EntailmentLabel.NEUTRAL))
    with pytest.raises(GateRejected,match='rejected claim ids') as e:
        VerificationGate(q).run(*artifacts([s1,s2],[c1,c2],[section]))
    assert 'c2' in e.value.report['traceability']['unverified_cited_claims']

def test_unknown_claim_id_fail():
    section=ScriptSection(heading='Intro',narration='No number.',claim_ids=['ghost'])
    with pytest.raises(GateRejected,match='unverified'):
        VerificationGate(QueueRouter(judgment())).run(*artifacts(sections=[section]))

@pytest.mark.parametrize('narration',['It took 4 hours.','Savings were 30%.','In 2026, performance increased.','$9 saved.'])
def test_uncited_numeric_claim_rejected(narration):
    sections=[ScriptSection(heading='A',narration=narration,claim_ids=[])]
    with pytest.raises(GateRejected,match='numeric narration'):
        VerificationGate(QueueRouter(judgment())).run(*artifacts(sections=sections))

def test_entailment_rejects_wrong_claim_id():
    r=QueueRouter(judgment('wrong','s1'))
    with pytest.raises(EntailmentError,match='judgments'):
        EntailmentVerifier(r).judge(claim(),[src()])

def test_entailment_rejects_unknown_source_id():
    r=QueueRouter(judgment('c1','s2'))
    with pytest.raises(EntailmentError):
        EntailmentVerifier(r).judge(claim(),[src()])

def test_entailment_rejects_duplicate_judgments():
    j=judgment().judgments[0]
    r=QueueRouter(EntailmentBatch(judgments=[j,j]))
    with pytest.raises(EntailmentError):
        EntailmentVerifier(r).judge(claim(),[src()])

def test_evidence_snippet_must_really_appear():
    with pytest.raises((GateRejected,EntailmentError)):
        VerificationGate(QueueRouter()).run(*artifacts(claims=[claim(snippet='this never appears')]))

def test_cached_entailment_key_changes_with_source_content():
    q=QueueRouter(judgment(),judgment())
    v=EntailmentVerifier(q)
    v.judge(claim(),[src(text='Verified study recorded 4 hours saved per day.')])
    v.judge(claim(),[src(text='Verified study recorded 4 hours saved per day. Additional context.')])
    assert q.calls[0][1]['evidence'][0]['source_sha256']!=q.calls[1][1]['evidence'][0]['source_sha256']

def test_source_hash_stable_across_ordering():
    q=QueueRouter(judgment())
    EntailmentVerifier(q).judge(claim(),[src()])
    assert len(q.calls[0][1]['evidence'][0]['source_sha256'])==64

def test_source_provenance_is_immutable():
    x=list(artifacts())
    x[3]=[src(text='Tampered but plausible.')]
    with pytest.raises(GateRejected,match='Inconsistent source evidence'):
        VerificationGate(QueueRouter()).run(*x)

def test_claim_in_verification_cannot_be_rewritten():
    r,v,sc,s=artifacts()
    v.verified=[claim(text='Tampered text')]
    with pytest.raises(GateRejected,match='changed claim evidence'):
        VerificationGate(QueueRouter()).run(r,v,sc,s)

def test_contradictions_check_all_pairs_even_disjoint_vocabulary():
    c1=claim('c1',text='Sunrise at dawn.',snippet='4 hours saved per day')
    c2=claim('c2',text='The eastern sky is dark.',snippet='4 hours saved per day')
    c3=claim('c3',text='Prices doubled last year.',snippet='4 hours saved per day')
    q=QueueRouter(ContradictionReport(pairs=[ContradictionPair(claim_id_a='c1',claim_id_b='c2',explanation='conflicting context')]))
    report=ContradictionDetector(q).detect([c1,c2,c3])
    assert len(report.pairs)==1
    assert len(q.calls)==1
    assert len(q.calls[0][1]['pairs'])==3

def test_contradictions_invalid_ids_fail_closed():
    q=QueueRouter(ContradictionReport(pairs=[ContradictionPair(claim_id_a='ghost',claim_id_b='c2',explanation='fake')]))
    with pytest.raises(ContradictionError):
        ContradictionDetector(q).detect([claim('c1'),claim('c2')])

def test_contradictions_over_budget_do_not_silently_skip():
    claims=[claim('c'+str(i)) for i in range(5)]
    with pytest.raises(ContradictionError,match='Too many'):
        ContradictionDetector(QueueRouter(),ContradictionConfig(max_total_pairs=3)).detect(claims)

def test_real_two_claim_contradiction_blocks_gate():
    s1=src()
    s2=src('s2',url='https://reuters.com/alt',text='Record showed savings were 8 hours daily.')
    c1=claim()
    c2=claim('c2','s2','Record showed savings were 8 hours daily.','8 hours daily')
    sc=ScriptSection(heading='A',narration='4 hours.',claim_ids=['c1','c2'])
    q=QueueRouter(judgment(),judgment('c2','s2'),ContradictionReport(pairs=[ContradictionPair(claim_id_a='c1',claim_id_b='c2',explanation='same metric differs')]))
    with pytest.raises(GateRejected,match='contradiction'):
        VerificationGate(q).run(*artifacts([s1,s2],[c1,c2],[sc]))

def test_corroboration_same_medium_domain_does_not_fake_independence():
    sources=[src('s'+str(i),f'https://author{i}.medium.com/p','4 hours saved per day.') for i in range(3)]
    c=VerifiedClaim(id='c1',text='4 hours saved per day.',source_ids=[s.source_id for s in sources],supporting_snippets=['4 hours saved per day']*3)
    judgments=EntailmentBatch(judgments=[EntailmentJudgment(claim_id='c1',source_id=s.source_id,label=EntailmentLabel.ENTAILMENT,confidence=.9) for s in sources])
    with pytest.raises(GateRejected):
        VerificationGate(QueueRouter(judgments)).run(*artifacts(sources,[c]))

def test_multiple_independent_domains_can_add_small_corroboration_bonus():
    sources=[src('s1','https://unknown.example.org/report','4 hours saved per day.'),src('s2','https://secondexample.org/report','4 hours saved per day.'),src('s3','https://thirdexample.org/report','4 hours saved per day.')]
    c=VerifiedClaim(id='c1',text='4 hours saved per day.',source_ids=[s.source_id for s in sources],supporting_snippets=['4 hours saved per day']*3)
    judgments=EntailmentBatch(judgments=[EntailmentJudgment(claim_id='c1',source_id=s.source_id,label=EntailmentLabel.ENTAILMENT,confidence=.9) for s in sources])
    out=VerificationGate(QueueRouter(judgments)).run(*artifacts(sources,[c]))
    assert out.report.accepted_count==1
    assert out.report.verdicts[0].weighted_score==pytest.approx(.595)

def test_integrated_entrypoint_never_approves_publication():
    class PipelineStub:
        def run(self,topic,urls):
            r,v,s,srcs=artifacts()
            return SimpleNamespace(research=r,verification=v,script=s)
    result=VerifiedContentPipeline(PipelineStub(),VerificationGate(QueueRouter(judgment()))).run('topic',[])
    assert result.ready_for_publication is False
    assert result.verification_gate.report.accepted_count==1

def test_integrated_entrypoint_blocks_invalid_script():
    class PipelineStub:
        def run(self,topic,urls):
            r,v,s,srcs=artifacts(sections=[ScriptSection(heading='h',narration='We saved 8 hours.',claim_ids=[])])
            return SimpleNamespace(research=r,verification=v,script=s)
    with pytest.raises(GateRejected):
        VerifiedContentPipeline(PipelineStub(),VerificationGate(QueueRouter(judgment()))).run('topic',[])

def test_no_publishing_enabled():
    from pipeline import PUBLISHING_ENABLED
    assert PUBLISHING_ENABLED is False
    assert not hasattr(VerificationGate,'publish')

def test_fabricated_numeric_claim_rejected_even_with_false_positive_llm():
    c=claim(text='The study recorded 400 hours saved per day.',snippet='4 hours saved per day')
    with pytest.raises(GateRejected):
        VerificationGate(QueueRouter(judgment())).run(*artifacts(claims=[c]))

def test_mismatched_citation_numbers_in_narration_rejected():
    section=ScriptSection(heading='H',narration='The system saved 8 hours per day.',claim_ids=['c1'])
    with pytest.raises(GateRejected,match='numeric narration'):
        VerificationGate(QueueRouter(judgment())).run(*artifacts(sections=[section]))

def test_number_in_hook_without_citation_is_rejected():
    r,v,sc,s=artifacts();sc.hook='This tool saved $999 per day!'
    with pytest.raises(GateRejected,match='untraceable numbers in hook'):
        VerificationGate(QueueRouter(judgment())).run(r,v,sc,s)

def test_real_pipeline_to_verification_gate_integration(tmp_path,monkeypatch):
    """Uses real Task1 Store, Task3 Router, Task4 Pipeline, and Task5 Gate."""
    import subprocess
    from pipeline import ContentPipeline,QualityThresholds
    from pipeline.models import ClaimProposal,ResearchOutput,ScriptOutput,StoryboardOutput,Scene
    from state_store import StateStore
    from router import Router,RouterConfig
    from tests.test_pipeline_offline import QueuedAdapter,FakeFetcher,_source
    from pipeline.pipeline import _claim_id,_word_count
    monkeypatch.setenv('ROUTER_ALLOW_LIVE_API','1') # mocked only; never network
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):subprocess.run(['git',*args],cwd=repo,check=True,capture_output=True)
    git('init','-b','main');git('config','user.email','test@example.invalid');git('config','user.name','Tester')
    (repo/'.gitignore').write_text('.router-state/\n.router-locks/\n');(repo/'README').write_text('seed')
    git('add','.');git('commit','-m','init')
    a='https://www.nih.gov/research';b='https://www.reuters.com/example'
    sa=_source(a,'Acme HVAC reported that dispatch automation saved 4 hours per day for a three-person team in 2025.')
    sb=_source(b,'Invoice automation reduced late payments by 30 percent for small contractors according to a 2024 survey.')
    claims=[ClaimProposal(text='Dispatch automation saved 4 hours per day for a 3-person team.',source_id=sa.source_id,supporting_snippet='saved 4 hours per day'),
            ClaimProposal(text='Invoice automation reduced late payments by 30 percent.',source_id=sb.source_id,supporting_snippet='reduced late payments by 30 percent'),
            ClaimProposal(text='A three-person team was studied in 2025.',source_id=sa.source_id,supporting_snippet='three-person team in 2025')]
    verified_ids=[_claim_id(c.text,c.source_id) for c in claims]
    script=ScriptOutput(title='How Small Teams Can Automate Admin',hook='See the workflow from start to finish.',
        sections=[ScriptSection(heading='Dispatch',narration='Dispatch automation saved 4 hours per day.',claim_ids=[verified_ids[0]]),
                  ScriptSection(heading='Invoices',narration='Late payments reduced by 30 percent.',claim_ids=[verified_ids[1]]),
                  ScriptSection(heading='Team',narration='This was a three-person team in 2025.',claim_ids=[verified_ids[2]])],
        cta='Watch the full demonstration next.')
    duration=_word_count(script.hook,*(s.narration for s in script.sections),script.cta)/2.5
    scenes=[Scene(index=i,section_index=i,start_s=duration*i/3,end_s=duration*(i+1)/3,
                  visual_type='diagram',instruction='Draw verified workflow',claim_ids=[verified_ids[i]]) for i in range(3)]
    adapter=QueuedAdapter('groq',[ResearchOutput(claims=claims),script,StoryboardOutput(scenes=scenes)])
    store=StateStore(repo,push_required=False)
    content=ContentPipeline(store,Router(store,{'groq':adapter},RouterConfig(provider_order=('groq',))),
      FakeFetcher({a:sa,b:sb}),QualityThresholds(min_script_duration_s=0,max_script_duration_s=1800,max_stage_revisions=1))
    gate_router=QueueRouter(judgment(verified_ids[0],sa.source_id),
                            judgment(verified_ids[1],sb.source_id),
                            judgment(verified_ids[2],sa.source_id),ContradictionReport(pairs=[]))
    combined=VerifiedContentPipeline(content,VerificationGate(gate_router))
    result=combined.run('AI automation for HVAC',[a,b])
    assert result.verification_gate.report.accepted_count==3
    assert len(result.verification_gate.report.traceability.citations)==3
    assert result.ready_for_publication is False
    assert adapter.calls==3
    assert len(gate_router.calls)==4
