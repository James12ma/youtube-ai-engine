import json
import pytest
from channel.queue import Topic,TopicQueue,load_queue,pick_next,queue_task_id

class StubState:
    def __init__(self,completed=()):self.completed=set(completed)
    def is_completed(self,tid):return tid in self.completed

def test_queue_picks_first_enabled_and_skips_completed():
    t1=Topic(topic='Small business invoicing',urls=['https://example.com/a','https://example.org/b'])
    t2=Topic(topic='Daily operations workflow',urls=['https://example.com/c','https://example.org/d'])
    queue=TopicQueue(topics=[t1,t2])
    assert pick_next(queue,StubState())==t1
    assert pick_next(queue,StubState([queue_task_id(t1)]))==t2
    assert pick_next(queue,StubState([queue_task_id(t1),queue_task_id(t2)])) is None

def test_rejects_invalid_sources(tmp_path):
    path=tmp_path/'queue.json'
    path.write_text(json.dumps({'topics':[{'topic':'Automating tasks for teams','urls':['http://example.com/x','https://example.org/y']}]}))
    with pytest.raises(ValueError,match='HTTPS'):load_queue(path)
