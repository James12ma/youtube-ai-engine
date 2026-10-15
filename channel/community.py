"""Bounded discussion discovery from evidence snapshots and original comment drafts.

No YouTube posting implementation or write credentials. Approval never posts.
"""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,model_validator

class Discussion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    video_id:str=Field(pattern=r'^[A-Za-z0-9_-]{11}$')
    channel_name:str=Field(min_length=3)
    title:str=Field(min_length=8)
    evidence_kind:Literal['description','transcript','public_comment','search_description']
    context:str=Field(min_length=30,max_length=2000)
    observed_at:datetime
    evidence_url:str=Field(pattern=r'^https://')
    established_channel_evidence:str=Field(min_length=20)
    relevance_reason:str=Field(min_length=25)
    contribution:str=Field(min_length=35,max_length=900)
    context_reviewed:bool=False
    @model_validator(mode='after')
    def safe(self):
        if self.observed_at.tzinfo is None:raise ValueError('Timezone required')
        if self.observed_at>datetime.now(timezone.utc)+timedelta(minutes=5):raise ValueError('Future evidence')
        return self


def _words(text):return set(re.findall(r'[a-z0-9]+',text.casefold()))

def discover(snapshots:list[Discussion],terms:list[str],limit=3):
    if not 1<=limit<=3:raise ValueError('Review at most three discussions')
    wanted=_words(' '.join(terms));ranked=[]
    for item in snapshots:
        overlap=len(wanted&_words(item.title+' '+item.context))
        if overlap and item.context_reviewed:ranked.append((overlap,item))
    return [x[1] for x in sorted(ranked,key=lambda x:(-x[0],x[1].video_id))[:limit]]


def draft_comments(discussions:list[Discussion],previous_texts=()):
    if len(discussions)>3:raise ValueError('No mass draft batches')
    drafts=[];seen=list(previous_texts);targets=set()
    for item in discussions:
        if not item.context_reviewed:raise ValueError('Review actual context before drafting')
        if item.video_id in targets:raise ValueError('One draft per discussion')
        text=item.contribution.strip()
        if re.search(r'https?://|www\.|subscribe|sub4sub|check out my|visit my|follow me',text,re.I):raise ValueError('Promotional/link draft rejected')
        if not (_words(text)&_words(item.context+' '+item.title)):raise ValueError('Contribution not topic-specific')
        for prior in seen:
            a,b=_words(text),_words(prior)
            if len(a&b)/max(1,len(a|b))>.65:raise ValueError('Repeated or near-duplicate draft')
        payload={'target_video_id':item.video_id,'target_url':'https://www.youtube.com/watch?v='+item.video_id,
            'channel':item.channel_name,'video_title':item.title,'comment':text,
            'evidence':item.model_dump(mode='json',exclude={'contribution'}),
            'draft_provenance':'Original editorial contribution supplied for this observed context; no fabricated viewer experience'}
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        drafts.append({**payload,'approval_digest':digest,'owner_approved':False,'posting_enabled':False,'status':'owner review required'})
        seen.append(text);targets.add(item.video_id)
    return drafts


def post_comment(*args,**kwargs):
    raise PermissionError('Posting is not implemented. Owner must approve the exact target and text; manual posting only.')


def export_drafts(path:Path,drafts):
    # Never overwrite a previous review or its approval state.
    with Path(path).open('x',encoding='utf-8') as file:json.dump({'posting_enabled':False,'drafts':drafts},file,indent=2)
