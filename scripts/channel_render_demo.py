"""Exercise the assembled renderer using observed original local UI behavior.

The verification report is an engineering fixture, explicitly labelled as such.
This is not live LLM research, owner editorial signoff or publication approval.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from pipeline.models import ScriptArtifact,ScriptSection,StoryboardOutput,Scene
from verification.models import VerificationGateReport,ClaimVerdict,EntailmentLabel,ContradictionReport,TraceabilityReport
from channel.video import render_approved_video


def run():
    out=Path('outputs/channel-render-demo');out.mkdir(parents=True,exist_ok=True)
    recorded=json.loads(Path('outputs/browser-demo/recording.json').read_text())
    now=datetime.now(timezone.utc).isoformat()
    text='Travel above one hundred dollars requires manager review in this original local demo.'
    script=ScriptArtifact(topic='Original local expense approval demo',
        title='Review the Rule Before You Automate',
        hook='Here is a working original expense approval demonstration.',
        sections=[ScriptSection(heading='A real local rule',
            narration=text+' We submit a travel expense of one hundred twenty dollars. The application sends the request for manager review.',
            on_screen_text='Real local rule, entered example data',claim_ids=['local-rule'])],
        cta='Check the rule and test the result before connecting any real business account.',
        duration_s=25,word_count=62,verified_at=now)
    gate=VerificationGateReport(topic=script.topic,verdicts=[ClaimVerdict(
        claim_id='local-rule',text=text,accepted=True,
        reason='Engineering fixture: actual local app.js and successful recorded DOM assertion; not live LLM verification',
        best_label=EntailmentLabel.ENTAILMENT,best_confidence=1,best_credibility=1,
        weighted_score=1,supporting_source_ids=['local-app.js'])],
        credibility=[],contradictions=ContradictionReport(),
        traceability=TraceabilityReport(),accepted_count=1,rejected_count=0,verified_at=now)
    storyboard=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=25,
        visual_type='screen_recording',instruction='Actual captured local app',claim_ids=['local-rule'])])
    for name,value in [('script',script),('verification_fixture',gate),('storyboard',storyboard)]:
        (out/(name+'.json')).write_text(value.model_dump_json(indent=2))
    report=render_approved_video(script,storyboard,gate,
        Path('voices/en_US-libritts-high.onnx'),out/'final.mp4',
        actual_assets={0:Path(recorded['video_path'])},reviewed=True)
    report['research_mode']='local engineering fixture; no live LLM'
    report['owner_approved']=False
    (out/'component_report.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
