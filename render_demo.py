from pathlib import Path
from pipeline.models import ScriptArtifact, ScriptSection, Scene, StoryboardOutput
from production import RenderConfig, EspeakOfflineBackend, render_video

script=ScriptArtifact(topic='engineering demonstration',title='Small Business Workflow Concept',hook='A better workflow starts with one clear problem.', sections=[ScriptSection(heading='Map the Process',narration='Map the steps your team follows. Then identify delays, and confirm every change with a real test.',on_screen_text='MAP. TEST. IMPROVE.',claim_ids=[])],cta='Follow for verified automation walkthroughs.', duration_s=14,word_count=29,verified_at='2026-10-13T00:00:00+00:00')
story=StoryboardOutput(scenes=[Scene(index=0,section_index=0,start_s=0,end_s=10,visual_type='diagram',instruction='Abstract process diagram only; no software demo',claim_ids=[])])
output=Path('/mnt/data/youtube_ai_task6_1080p_engineering_demo.mp4')
report=render_video(script,story,output,EspeakOfflineBackend(),config=RenderConfig(width=1920,height=1080,fps=24,crf=27,preset='ultrafast',caption_size=48,temp_scale=1),workdir=Path('/mnt/data/youtube_router_v3_task6_review/render_demo_assets'),approved=True)
Path('/mnt/data/youtube_router_v3_task6_review/demo_report.json').write_text(report.model_dump_json(indent=2))
print(report.model_dump_json(indent=2))
