"""Git-backed source-first editorial queue. Never auto-uploads.

Queue entries must provide at least two HTTPS research sources explicitly;
no hallucinated research links and no scraping private/internal networks.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel,Field
from state_store import StateStore,compute_task_id

class Topic(BaseModel):
    topic:str = Field(min_length=8,max_length=200)
    urls:list[str] = Field(min_length=2,max_length=8)
    enabled:bool = True

class TopicQueue(BaseModel):
    topics:list[Topic] = Field(min_length=1)


def _validate_queue(queue:TopicQueue)->None:
    for item in queue.topics:
        if len(set(item.urls))<2:raise ValueError('Two distinct HTTPS sources required')
        for url in item.urls:
            p=urlparse(url)
            if p.scheme!='https' or not p.hostname or p.username or p.password:
                raise ValueError('Only public HTTPS source URLs permitted')

def load_queue(path:Path)->TopicQueue:
    result=TopicQueue.model_validate_json(Path(path).read_text(encoding='utf-8'))
    _validate_queue(result)
    return result

def queue_task_id(item:Topic)->str:
    return compute_task_id('channel.editorial_queue',{'topic':item.topic,'urls':sorted(item.urls)},'1.0')

def pick_next(queue:TopicQueue,state:StateStore)->Topic|None:
    for item in queue.topics:
        if item.enabled and not state.is_completed(queue_task_id(item)):
            return item
    return None

def run_next(queue_path:Path,repo_path:Path,out_root:Path,*,allow_live:bool=False)->dict:
    from .research import generate_draft
    state=StateStore(repo_path,push_required=True)
    state.pull()
    queue=load_queue(queue_path)
    item=pick_next(queue,state)
    if item is None:return {'status':'empty','draft_created':False}
    tid=queue_task_id(item)
    folder=Path(out_root)/re.sub(r'[^a-z0-9]+','-',item.topic.lower()).strip('-')[:48]
    folder=folder.with_name(folder.name+'-'+tid[:8])
    # Fail closed. Don't create an empty workdir before permission checks.
    result=generate_draft(repo_path,item.topic,item.urls,folder,allow_live=allow_live)
    state.pull()
    state.record_completion(tid,'channel.editorial_queue',{'draft_id':tid,'files':result['files']})
    return {'status':'draft_created','draft_dir':str(folder),'needs_human_review':True}
