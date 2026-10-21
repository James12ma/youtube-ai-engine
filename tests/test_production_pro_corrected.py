from pathlib import Path
import pytest
from production_pro.models import EvidenceDataset,EvidencePoint,NarrationResult,NarrationSegment,EditPlan
from production_pro.errors import ChartError,EditingError
from production_pro.captions import write_captions
from production_pro.editing import compose_scenes
from production_pro.recorder import WorkflowRecorder

def test_captions_are_explicitly_approximate(tmp_path):
 n=NarrationResult(segments=[NarrationSegment(text='A few example words with neat captions.',audio_path='x.wav',duration_s=3.)],total_duration_s=3.,backend='espeak')
 count,coverage,real=write_captions(n,tmp_path/'cap.ass',1280,720,max_chars=16)
 assert count>=1 and .9<=coverage<=1.0 and real is False
 assert r'\N' in (tmp_path/'cap.ass').read_text()

def test_recording_block_nonlocal_url(tmp_path):
 with pytest.raises(Exception):WorkflowRecorder('https://example.com',tmp_path).record([])

def test_piper_requires_real_models(tmp_path):
 from production_pro.narration import PiperNarrator
 with pytest.raises(Exception):PiperNarrator(tmp_path/'missing.onnx')

def test_edit_rejects_out_of_bounds_highlight(tmp_path):
 from PIL import Image
 p=tmp_path/'image.png';Image.new('RGB',(200,100),'blue').save(p)
 plan=EditPlan(scene_index=0,source_path=str(p),duration_s=1,highlight_rect=[199,90,100,50])
 with pytest.raises(EditingError):compose_scenes([plan],tmp_path/'absent.wav',tmp_path/'bad.mp4',width=200,height=100,workdir=tmp_path/'w')
