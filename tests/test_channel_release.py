from __future__ import annotations
import json,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from channel.metadata import generate_metadata
from channel.thumbnail import make_thumbnail
from channel.release import build_release,approve_release,check_approval,ReleaseError
from channel.youtube import upload_youtube,UploadBlocked
from pipeline.models import ScriptArtifact,ScriptSection,ResearchArtifact,Source
from verification.models import (VerificationGateReport,ClaimVerdict,
    EntailmentLabel,ContradictionReport,TraceabilityReport,TracedClaim)


def sample_artifacts():
    source=Source(source_id='s1',url='https://example.com/research',title='Research',
        retrieved_at='2026-10-01T00:00:00+00:00',text='Source-backed workflow research.')
    from pipeline.models import VerifiedClaim
    claim=VerifiedClaim(id='c1',text='Automations can streamline workflows',
        source_ids=['s1'],supporting_snippets=['workflow research'])
    research=ResearchArtifact(topic='AI automation workflows',sources=[source],claims=[claim],
        rejected_claims=[],retrieved_at='2026-10-01T00:00:00+00:00')
    script=ScriptArtifact(topic='AI automation workflows',title='How to Review AI Automation Workflows',
        hook='Do you know your workflow?',
        sections=[ScriptSection(heading='Checklist',narration='Use a checklist before changing a workflow.',
                   claim_ids=['c1'])],cta='Subscribe for more practical walkthroughs.',
        duration_s=20,word_count=32,verified_at='2026-10-01T00:00:00+00:00')
    verdict=ClaimVerdict(claim_id='c1',text=claim.text,accepted=True,reason='test',
            best_label=EntailmentLabel.ENTAILMENT,best_confidence=.9,best_credibility=.8,
            weighted_score=.72,supporting_source_ids=['s1'])
    cited=TracedClaim(section_index=0,claim_id='c1',source_ids=['s1'],
        source_urls=['https://example.com/research'],supporting_snippets=['workflow research'],
        best_label=EntailmentLabel.ENTAILMENT,best_credibility=.8)
    gate=VerificationGateReport(topic=research.topic,verdicts=[verdict],credibility=[],
         contradictions=ContradictionReport(pairs=[]),traceability=TraceabilityReport(citations=[cited]),
         accepted_count=1,rejected_count=0,verified_at='2026-10-01T00:00:00+00:00')
    return script,research,gate


def test_metadata_only_uses_verified_source():
    script,research,gate=sample_artifacts();meta=generate_metadata(script,research,gate)
    assert 'https://example.com/research' in meta.description
    assert meta.category_id=='27' and meta.made_for_kids is False


def test_metadata_rejects_uncited():
    script,research,gate=sample_artifacts()
    gate.traceability.citations=[]
    with pytest.raises(ValueError,match='No traceable'):
        generate_metadata(script,research,gate)


def test_thumbnail_is_real_image_and_numeric_results_guarded(tmp_path):
    image=make_thumbnail('Review Your Workflow',tmp_path/'thumb.jpg')
    from PIL import Image
    with Image.open(image) as picture:assert picture.size==(1280,720)
    with pytest.raises(ValueError,match='Numeric'):
        make_thumbnail('Save 98% Today',tmp_path/'wrong.jpg')


def create_release(tmp_path:Path):
    from channel.metadata import ReleaseMetadata
    thumb=make_thumbnail('Review Your Workflow',tmp_path/'thumb.jpg')
    video=tmp_path/'video.mp4'
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
         '-f','lavfi','-i','color=c=blue:s=320x180:d=1:r=10',
         '-f','lavfi','-i','sine=frequency=220:duration=1',
         '-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',str(video)],
         capture_output=True,check=True)
    report=tmp_path/'editorial.json';report.write_text(json.dumps({
        'gate_passed':True,'human_reviewed':True,'quality_passed':True,
        'reviewed_by':'owner'}))
    folder=tmp_path/'release'
    manifest=build_release(folder,video,thumb,ReleaseMetadata(title='Review AI Workflows',description='Educational demonstration.',contains_synthetic_media=False),
                          editorial_report=report)
    return folder,manifest


def test_release_approval_and_tamper(tmp_path):
    folder,manifest=create_release(tmp_path)
    with pytest.raises(ReleaseError):check_approval(folder)
    with pytest.raises(ReleaseError):approve_release(folder,'bad',human_confirmed=True)
    approve_release(folder,manifest['release_digest'],human_confirmed=True)
    check_approval(folder)
    (folder/'metadata.json').write_text('{}')
    with pytest.raises(ReleaseError,match='changed'):check_approval(folder)


def test_upload_private_requires_two_gates(tmp_path,monkeypatch):
    folder,manifest=create_release(tmp_path)
    approve_release(folder,manifest['release_digest'],human_confirmed=True)
    with pytest.raises(UploadBlocked,match='disabled'):upload_youtube(folder)
    monkeypatch.setenv('YOUTUBE_UPLOAD_ALLOWED','1')
    with pytest.raises(UploadBlocked,match='digest'):upload_youtube(folder)
    monkeypatch.setenv('OWNER_APPROVED_RELEASE_DIGEST',manifest['release_digest'])
    token=tmp_path/'token.json';token.write_text('{}')
    monkeypatch.setenv('YOUTUBE_TOKEN_FILE',str(token))
    with pytest.raises(UploadBlocked,match='disabled'):
        upload_youtube(folder,privacy='public')


def test_fake_youtube_private_receipt(tmp_path,monkeypatch):
    folder,manifest=create_release(tmp_path)
    approve_release(folder,manifest['release_digest'],human_confirmed=True)
    monkeypatch.setenv('YOUTUBE_UPLOAD_ALLOWED','1')
    monkeypatch.setenv('OWNER_APPROVED_RELEASE_DIGEST',manifest['release_digest'])
    token=tmp_path/'token.json';token.write_text('{}');monkeypatch.setenv('YOUTUBE_TOKEN_FILE',str(token))
    calls=[]
    class Request:
        def next_chunk(self):return None,{'id':'TEST_VIDEO_ID'}
    class Videos:
        def insert(self,**kwargs):calls.append(kwargs);return Request()
    class Youtube:
        def videos(self):return Videos()
    receipt=upload_youtube(folder,api_factory=lambda:(Youtube(),lambda path:None))
    assert receipt['youtube_video_id']=='TEST_VIDEO_ID'
    assert calls[0]['body']['status']['privacyStatus']=='private'
    with pytest.raises(UploadBlocked,match='Receipt already exists'):upload_youtube(folder,api_factory=lambda:(Youtube(),lambda p:None))
