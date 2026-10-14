"""Genuine local browser recording: no browser network requests, no APIs."""
from pathlib import Path
from production_pro.recorder import WorkflowRecorder

def test_local_browser_records_real_rule(tmp_path:Path):
 seen=[]
 def fill(p):
  p.locator('#amount').fill('120')
  p.locator('#category').select_option('travel')
  p.locator('#submit').click()
  result=p.locator('#result').inner_text()
  seen.append(result)
 assert WorkflowRecorder('local-inline-demo',tmp_path/'rec',viewport=(640,360)).record([('submit',fill)]).duration_s>0.4
 assert seen==['SENT FOR MANAGER REVIEW · $120 · travel']
