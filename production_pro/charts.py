"""Only produce numeric charts for data validated by an explicit source-and-claim resolver."""
from __future__ import annotations
import re
from pathlib import Path
from urllib.parse import urlsplit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .models import EvidenceDataset
from .errors import ChartError

NUM=re.compile(r'(?<![\d.])\d+(?:\.\d+)?(?!\d)')

def validate_evidence(dataset:EvidenceDataset,verified_claims:dict[str,dict],source_texts:dict[str,str])->None:
 if not dataset.points:raise ChartError('no points')
 for p in dataset.points:
  if urlsplit(p.source_url).scheme!='https' or not urlsplit(p.source_url).hostname:raise ChartError('invalid source url')
  if not p.source_snippet.strip() or not p.source_id or not p.claim_id:raise ChartError('missing provenance')
  c=verified_claims.get(p.claim_id)
  if not c or not c.get('accepted') or p.source_id not in c.get('source_ids',[]):raise ChartError('claim not verified by Task 5')
  source=source_texts.get(p.source_id)
  if not source or ' '.join(p.source_snippet.lower().split()) not in ' '.join(source.lower().split()):raise ChartError('snippet not in retrieved source')
  # Structural data integrity: numbers have to be found exactly in the snippet.
  numbers={float(x) for x in NUM.findall(p.source_snippet.replace(',',''))}
  if round(p.value,5) not in {round(x,5) for x in numbers}:
   raise ChartError('chart value not found in cited excerpt')

def render_bar_chart(dataset:EvidenceDataset,output:Path,verified_claims:dict[str,dict],source_texts:dict[str,str])->Path:
 validate_evidence(dataset,verified_claims,source_texts)
 fig,ax=plt.subplots(figsize=(12,6.75),dpi=160)
 fig.set_facecolor('#101420');ax.set_facecolor('#101420')
 ax.barh([p.label for p in dataset.points],[p.value for p in dataset.points],color='#70e7c4')
 ax.set_title(dataset.title,color='white');ax.set_xlabel(dataset.y_axis_label,color='white');ax.tick_params(colors='white')
 for i,p in enumerate(dataset.points):
  ax.text(p.value,i,f'  {p.source_id}',va='center',color='white',fontsize=9)
 fig.tight_layout();output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(output,facecolor=fig.get_facecolor());plt.close(fig)
 return output
