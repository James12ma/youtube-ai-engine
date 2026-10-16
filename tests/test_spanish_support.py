"""Spanish narration support: prompts, script language, alignment tokens, metadata."""
from __future__ import annotations
import importlib, os
import pytest
from pipeline import ContentPipeline, QualityThresholds
from pipeline.models import ScriptOutput, ScriptSection, VerificationArtifact, VerifiedClaim
from state_store import StateStore
from tests.test_pipeline_offline import FakeFetcher, _init_repo


def test_unsupported_language_rejected(tmp_path):
    with pytest.raises(ValueError, match='Unsupported narration language'):
        ContentPipeline(StateStore(_init_repo(tmp_path/'r'), push_required=False), None, FakeFetcher({}),
                        QualityThresholds(language='fr'))


def test_spanish_prompts_and_script_language(tmp_path):
    ids=['c1']
    verification=VerificationArtifact(topic='ITIN',verified=[VerifiedClaim(id='c1',text='Evidencia',source_ids=['s'],supporting_snippets=['Evidencia'])],rejected=[],pass_rate=1,verified_at='now')
    full=ScriptOutput(title='Qué es el ITIN',hook='Empiece aquí.',cta='Gracias por ver.',
        sections=[ScriptSection(heading='S'+str(i),narration=' '.join(['palabra']*170),claim_ids=ids) for i in range(8)])
    prompts=[]
    class Router_:
        def execute(self,task_type,input_data,request,schema):
            prompts.append(request.messages[-1]['content']);return full
    pipe=ContentPipeline(StateStore(_init_repo(tmp_path/'r'),push_required=False),Router_(),FakeFetcher({}),QualityThresholds(language='es'))
    out=pipe._stage_script('ITIN',verification,[])
    assert out.language=='es' and 'español neutro' in prompts[0]
    en=ContentPipeline(StateStore(_init_repo(tmp_path/'e'),push_required=False),Router_(),FakeFetcher({}))
    assert en._stage_script('ITIN',verification,[]).language=='en'
    assert 'español' not in prompts[-1]


def test_aligner_tokens_keep_accented_words_whole():
    from narration_pro.aligner import _tokens
    assert _tokens('Información del año: ¿Qué es el ITIN?')==['información','del','año','qué','es','el','itin']
    assert _tokens("Don't stop, it's 2025")==["don't",'stop',"it's",'2025']


def test_spanish_metadata_text():
    from channel import metadata as m
    from pipeline.models import ScriptArtifact
    s=ScriptArtifact(language='es',topic='el ITIN',title='Qué es el ITIN',hook='Muchas personas lo necesitan. Más texto.',cta='Gracias.',
        sections=[ScriptSection(heading='Quién lo necesita',narration='x'),ScriptSection(heading='Cómo solicitarlo',narration='x')],
        duration_s=1,word_count=1,verified_at='now')
    intro=m.description_intro(s)
    assert intro.startswith('Muchas personas lo necesitan.') and 'En este video explicamos el ITIN' in intro and ' y ' in intro
    assert 'no es asesoría fiscal' in m._TEXT['es']['footer']


def test_research_check_reads_owner_topic_sources_language(monkeypatch):
    import scripts.check_research_pipeline as crp
    monkeypatch.setenv('RESEARCH_TOPIC','  Qué es el   ITIN ')
    monkeypatch.setenv('RESEARCH_SOURCES','https://www.irs.gov/es/a https://www.irs.gov/es/b')
    monkeypatch.setenv('CONTENT_LANGUAGE','es')
    assert crp._configured()==('Qué es el ITIN',('https://www.irs.gov/es/a','https://www.irs.gov/es/b'),'es')
    monkeypatch.setenv('RESEARCH_SOURCES','http://insecure.example/a https://www.irs.gov/b')
    with pytest.raises(ValueError,match='HTTPS'):crp._configured()
    monkeypatch.setenv('RESEARCH_SOURCES','https://www.irs.gov/only-one')
    with pytest.raises(ValueError,match='Between 2 and 8'):crp._configured()
    for k in ('RESEARCH_TOPIC','RESEARCH_SOURCES','CONTENT_LANGUAGE'):monkeypatch.delenv(k)
    assert crp._configured()==(crp.DEFAULT_TOPIC,crp.DEFAULT_SOURCES,'en')


def test_storyboard_prompt_avoids_footage_scenes_by_default(tmp_path):
    from pipeline.models import ScriptArtifact, StoryboardOutput, Scene
    script=ScriptArtifact(language='es',topic='t',title='T',hook='h',cta='c',duration_s=10,word_count=25,verified_at='now',
        sections=[ScriptSection(heading='A',narration=' '.join(['w']*20))])
    prompts=[]
    class Router_:
        def execute(self,task_type,input_data,request,schema):
            prompts.append(request.messages[0]['content'])
            return StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=10,visual_type='diagram',instruction='x')])
    verification=VerificationArtifact(topic='t',verified=[],rejected=[],pass_rate=1,verified_at='now')
    ContentPipeline(StateStore(_init_repo(tmp_path/'a'),push_required=False),Router_(),FakeFetcher({}))._stage_storyboard(script,verification,[])
    assert 'never use screen_recording, chart or broll' in prompts[-1]
    ContentPipeline(StateStore(_init_repo(tmp_path/'b'),push_required=False),Router_(),FakeFetcher({}),QualityThresholds(footage_available=True))._stage_storyboard(script,verification,[])
    assert 'never use' not in prompts[-1]
